<#
.SYNOPSIS
  YES-NK 桌面分身一次性设定与一键还原脚本（与 YES-BD2 完全一致的 Windows Child Session 方案）。

.DESCRIPTION
  在项目根目录运行，会请求一次管理员权限 (UAC)：

      powershell -NoProfile -ExecutionPolicy Bypass -File tools\clone_desktop\setup.ps1
      powershell -NoProfile -ExecutionPolicy Bypass -File tools\clone_desktop\setup.ps1 -Undo

  本脚本会做以下设定（-Undo 会逐项完整还原）：
  - 使用 Windows 自带 .NET 4.0 csc.exe 编译 CloneDesktop.exe 到 %LOCALAPPDATA%\yes-nk\clone-desktop；
  - 写入 HKCU\Software\Microsoft\Terminal Server Client\RemoteDesktop_SuppressWhenMinimized = 2，
    使桌面分身窗口最小化后仍保持 1920x1080 画面渲染；
  - 请求一次管理员权限开启 Windows 子会话 (WTSEnableChildSessions)，不开放外部远程桌面端口；
  - 仅在传入 -AllowRdp 时才启用兼容兜底：先添加拦截其他电脑入站 RDP 的防火墙规则，再启用本地 TermService。

  编译参数与注册表项参考自 ChildStream 与 YES-BD2（MIT，见 LICENSE-childstream.txt）。
#>
param(
    [switch]$Undo,
    [switch]$NoPause,
    [switch]$AllowRdp,
    # 内部参数：提权后的管理员子进程
    [switch]$AdminPart,
    [string]$DataDir
)

$ErrorActionPreference = 'Stop'
if (-not $DataDir) { $DataDir = Join-Path $env:LOCALAPPDATA 'yes-nk\clone-desktop' }
New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
$logFile = Join-Path $DataDir 'setup.log'
$stateFile = Join-Path $DataDir 'setup-state.json'
$exe = Join-Path $DataDir 'CloneDesktop.exe'
$tsKey = 'HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server'
$clientKey = 'HKCU:\Software\Microsoft\Terminal Server Client'

function Say([string]$text) {
    Write-Host $text
    $line = '{0} {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $text
    Add-Content -LiteralPath $logFile -Value $line -Encoding UTF8
}

function Read-State {
    $state = @{}
    if (Test-Path -LiteralPath $stateFile) {
        $json = Get-Content -LiteralPath $stateFile -Raw -Encoding UTF8 | ConvertFrom-Json
        foreach ($p in $json.PSObject.Properties) { $state[$p.Name] = $p.Value }
    }
    $state
}

function Write-State($state) {
    $state | ConvertTo-Json | Set-Content -LiteralPath $stateFile -Encoding UTF8
}

Add-Type -Namespace YesNk -Name ChildSessions -MemberDefinition @'
[DllImport("wtsapi32.dll")]
public static extern bool WTSEnableChildSessions(bool enable);
[DllImport("wtsapi32.dll")]
public static extern bool WTSIsChildSessionsEnabled(out bool enabled);
[DllImport("wtsapi32.dll")]
public static extern bool WTSGetChildSessionId(out uint sessionId);
'@

function Test-ChildSessions {
    $on = $false
    [void][YesNk.ChildSessions]::WTSIsChildSessionsEnabled([ref]$on)
    $on
}

function Invoke-Native([scriptblock]$command) {
    $saved = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try { & $command 2>&1 | Out-String } finally { $ErrorActionPreference = $saved }
}

$blockRuleNames = 'yes-nk-clone-desktop-block-rdp-tcp', 'yes-nk-clone-desktop-block-rdp-udp'

function Add-RdpBlockRules {
    $port = (Get-ItemProperty -Path "$tsKey\WinStations\RDP-Tcp" -ErrorAction SilentlyContinue).PortNumber
    if (-not $port) { $port = 3389 }
    foreach ($protocol in 'TCP', 'UDP') {
        $name = 'yes-nk-clone-desktop-block-rdp-' + $protocol.ToLower()
        Remove-NetFirewallRule -Name $name -ErrorAction SilentlyContinue
        New-NetFirewallRule -Name $name -DisplayName "YES-NK 桌面分身：拦截其他电脑连接远程桌面 ($protocol $port)" `
            -Direction Inbound -Action Block -Protocol $protocol -LocalPort $port -Profile Any | Out-Null
    }
    Say "防火墙：已添加拦截规则阻挡其他电脑连入远程桌面（端口 $port，本机分身连接不受影响）"
}

function Invoke-AdminPart {
    $state = Read-State
    if ($Undo) {
        $id = [uint32]0
        if ([YesNk.ChildSessions]::WTSGetChildSessionId([ref]$id) -and $id -ne 0 -and $id -ne [uint32]::MaxValue) {
            Say "正在注销桌面分身（会话 $id），分身内的程序将会关闭"
            Invoke-Native { logoff.exe $id } | Out-Null
            Start-Sleep -Seconds 3
        }
        if ($state.ContainsKey('childSessionsBefore') -and $state['childSessionsBefore']) {
            Say '设定前桌面分身功能本来就已开启，保持原样'
        } else {
            [void][YesNk.ChildSessions]::WTSEnableChildSessions($false)
            Say ('关闭桌面分身功能：{0}' -f $(if (Test-ChildSessions) { '失败，仍处于开启状态' } else { '已关闭' }))
        }
        if ($state.ContainsKey('denyBefore')) {
            $deny = 1
            if ($null -ne $state['denyBefore']) { $deny = [int]$state['denyBefore'] }
            Set-ItemProperty -Path $tsKey -Name fDenyTSConnections -Value $deny -Type DWord
            Say "fDenyTSConnections 已改回 $deny（1 = 不允许远程桌面连接）"
        }
        foreach ($name in $blockRuleNames) {
            if (Get-NetFirewallRule -Name $name -ErrorAction SilentlyContinue) {
                Remove-NetFirewallRule -Name $name
                Say "已移除防火墙规则 $name"
            }
        }
        return
    }

    if ($AllowRdp) {
        $off = @(Get-NetFirewallProfile | Where-Object { "$($_.Enabled)" -ne 'True' } | ForEach-Object { $_.Name })
        if ($off.Count) {
            throw ('Windows 防火墙的 {0} 配置文件处于关闭状态，为防止其他电脑连入，未开启远程桌面且未作任何修改' -f ($off -join '、'))
        }
    }
    if (-not $state.ContainsKey('childSessionsBefore')) {
        $state['childSessionsBefore'] = Test-ChildSessions
        Write-State $state
    }
    [void][YesNk.ChildSessions]::WTSEnableChildSessions($true)
    if (-not (Test-ChildSessions)) { throw '无法开启桌面分身功能（WTSEnableChildSessions 返回失败）' }
    Say '桌面分身功能：已开启'
    if (-not $AllowRdp) { return }

    if (-not $state.ContainsKey('denyBefore')) {
        $state['denyBefore'] = (Get-ItemProperty -Path $tsKey -Name fDenyTSConnections -ErrorAction SilentlyContinue).fDenyTSConnections
        Write-State $state
    }
    Add-RdpBlockRules
    Set-ItemProperty -Path $tsKey -Name fDenyTSConnections -Value 0 -Type DWord
    Say 'fDenyTSConnections = 0（允许本机连接桌面分身）'
    $service = Get-Service -Name TermService
    if ($service.Status -ne 'Running') {
        if ("$($service.StartType)" -eq 'Disabled') { throw '「远程桌面服务」(TermService) 已被禁用，桌面分身需要该服务' }
        Start-Service -Name TermService
        Say '已启动「远程桌面服务」(TermService)'
    }
}

function Invoke-Elevated {
    if (([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
            [Security.Principal.WindowsBuiltInRole]::Administrator)) {
        Invoke-AdminPart
        return $true
    }
    $psExe = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
    if (-not (Test-Path -LiteralPath $psExe)) { $psExe = 'powershell.exe' }
    $argList = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$PSCommandPath`"",
        '-AdminPart', '-DataDir', "`"$DataDir`"")
    if ($Undo) { $argList += '-Undo' }
    if ($AllowRdp) { $argList += '-AllowRdp' }
    $before = if (Test-Path -LiteralPath $logFile) { @(Get-Content -LiteralPath $logFile -Encoding UTF8).Count } else { 0 }
    Write-Host '弹出「用户账户控制 (UAC)」提示时请点击「是」。'
    try {
        $p = Start-Process -FilePath $psExe -ArgumentList $argList -Verb RunAs -Wait -PassThru -WindowStyle Hidden
    } catch {
        Say '未允许管理员权限，系统设定未修改。'
        return $false
    }
    if (Test-Path -LiteralPath $logFile) {
        Get-Content -LiteralPath $logFile -Encoding UTF8 | Select-Object -Skip $before | ForEach-Object { Write-Host $_ }
    }
    if ($null -ne $p -and $p.ExitCode -ne 0) {
        Say ('管理员设定子进程异常退出（代码 {0}），请查看日志：{1}' -f $p.ExitCode, $logFile)
        return $false
    }
    $true
}

function Install {
    Say '=== 设定 YES-NK 桌面分身 ==='
    $edition = (Get-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion').EditionID
    if ($edition -like 'Core*') { throw "当前系统为 Windows 家庭版（$edition），不支持 Windows 子会话桌面分身" }
    Say "Windows 版本：$edition"

    $serviceDll = (Get-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Services\TermService\Parameters' -ErrorAction SilentlyContinue).ServiceDll
    if ($serviceDll -and $serviceDll -notlike '*\termsrv.dll') {
        Say "注意：远程桌面服务 DLL 被替换为 $serviceDll（如 RDP Wrapper），桌面分身可能无法连接"
    }

    $termService = Get-CimInstance -ClassName Win32_Service -Filter "Name='TermService'" -ErrorAction SilentlyContinue
    if (-not $termService) {
        $svcFallback = Get-Service -Name TermService -ErrorAction SilentlyContinue
        if (-not $svcFallback) {
            throw '本机缺少「远程桌面服务」(TermService)，无法使用桌面分身（常见于精简版 Windows 或优化工具）'
        }
        if ("$($svcFallback.StartType)" -eq 'Disabled') {
            Say '注意：「远程桌面服务」已被禁用，请在 YES-NK 桌面分身页面点击「帮我打开」。'
        }
    } elseif ($termService.StartMode -eq 'Disabled') {
        Say '注意：「远程桌面服务」已被禁用，请在 YES-NK 桌面分身页面点击「帮我打开」。'
    }

    $csc = Join-Path $env:SystemRoot 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
    if (-not (Test-Path -LiteralPath $csc)) { $csc = Join-Path $env:SystemRoot 'Microsoft.NET\Framework\v4.0.30319\csc.exe' }
    if (-not (Test-Path -LiteralPath $csc)) { throw '未找到 .NET Framework 4.0 csc.exe，无法编译 CloneDesktop.exe' }

    $source = Join-Path $PSScriptRoot 'CloneDesktop.cs'
    $output = Invoke-Native {
        & $csc /nologo /codepage:65001 /target:winexe "/out:$exe" /r:System.Windows.Forms.dll /r:System.Drawing.dll `
            /r:Microsoft.CSharp.dll /r:System.Core.dll /r:System.Management.dll $source
    }
    if ($LASTEXITCODE -ne 0) {
        Say $output
        throw '编译 CloneDesktop.exe 失败'
    }
    Say "已生成桌面分身窗口程序：$exe"

    if (-not (Invoke-Elevated)) { return $false }
    if (-not (Test-ChildSessions)) { throw "桌面分身功能未成功开启，请查看日志：$logFile" }

    $state = Read-State
    if (-not $state.ContainsKey('suppressBefore')) {
        $state['suppressBefore'] = (Get-ItemProperty -Path $clientKey -Name RemoteDesktop_SuppressWhenMinimized -ErrorAction SilentlyContinue).RemoteDesktop_SuppressWhenMinimized
        Write-State $state
    }
    New-Item -Path $clientKey -Force | Out-Null
    Set-ItemProperty -Path $clientKey -Name RemoteDesktop_SuppressWhenMinimized -Value 2 -Type DWord
    Say 'RemoteDesktop_SuppressWhenMinimized = 2（分身窗口最小化后仍继续渲染画面）'

    $passwordless = (Get-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\PasswordLess\Device' -ErrorAction SilentlyContinue).DevicePasswordLessBuildVersion
    if ($passwordless -eq 2) {
        Say '注意：当前电脑开启了「仅允许 Microsoft 账户使用 Windows Hello 登录」。可在 YES-NK 桌面分身页点击「帮我关掉」，或到系统「设置 > 账户 > 登录选项」关闭该项（人脸与 PIN 无需关闭）。'
    }

    Say "完成！现在可以回到 YES-NK 点击「在桌面分身跑」。"
    Say "如需完全还原：powershell -NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`" -Undo"
    $true
}

function Uninstall {
    Say '=== 还原 YES-NK 桌面分身 ==='
    if (-not (Invoke-Elevated)) { return $false }
    Say ('当前状态：桌面分身功能 {0}，fDenyTSConnections = {1}' -f $(if (Test-ChildSessions) { '开启' } else { '关闭' }), (Get-ItemProperty -Path $tsKey).fDenyTSConnections)
    $state = Read-State
    $before = $null
    if ($state.ContainsKey('suppressBefore')) { $before = $state['suppressBefore'] }
    if ($null -eq $before) {
        Remove-ItemProperty -Path $clientKey -Name RemoteDesktop_SuppressWhenMinimized -ErrorAction SilentlyContinue
        Say '已删除 RemoteDesktop_SuppressWhenMinimized'
    } else {
        Set-ItemProperty -Path $clientKey -Name RemoteDesktop_SuppressWhenMinimized -Value ([int]$before) -Type DWord
        Say "RemoteDesktop_SuppressWhenMinimized 已改回 $before"
    }
    foreach ($name in 'CloneDesktop.exe', 'setup-state.json') {
        $path = Join-Path $DataDir $name
        if (Test-Path -LiteralPath $path) {
            Remove-Item -LiteralPath $path -Force
            Say "已删除 $path"
        }
    }
    Say "还原完成。日志文件保留在 $DataDir（setup.log、viewer.log）。"
    $true
}

$ok = $false
try {
    if ($AdminPart) {
        Invoke-AdminPart
        exit 0
    }
    if (Get-Process -Name CloneDesktop -ErrorAction SilentlyContinue) {
        throw '桌面分身窗口仍在运行，请先关闭它（右键右下角托盘图标 > 结束分身）后再执行'
    }
    if ($Undo) { $ok = Uninstall } else { $ok = Install }
} catch {
    Say ('出错：' + $_.Exception.Message)
    if ($AdminPart) { exit 1 }
}

if (-not $NoPause) { Read-Host '按 Enter 关闭窗口' | Out-Null }
if ($ok) { exit 0 } else { exit 1 }
