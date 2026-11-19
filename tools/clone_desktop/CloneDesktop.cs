// YES-NK 桌面分身窗口程序（与 nobell001/YES-BD2 完全一致的 Windows Child Session RDP 方案）。
// 参考 ChildStream (MIT, 见 LICENSE-childstream.txt) 与 YES-BD2 CloneDesktop.cs 设计。
//
// 用法（由 tools\clone_desktop\setup.ps1 使用系统自带 .NET 4.0 csc.exe 编译）：
//   CloneDesktop.exe              打开桌面分身窗口
//   CloneDesktop.exe -user NAME   在 Windows 登录框预填账号名称
//   CloneDesktop.exe -move URI    关闭时提供「搬回桌面」选项：注销分身后在主桌面打开目标程序/URI
//   CloneDesktop.exe -launch EXE -args ARGS -cwd DIR
//                                 登录分身后通过一次性计划任务在子会话内自动拉起 YES-NK
//                                 结果写入 launch-result.txt
//   CloneDesktop.exe -check       检查系统是否开启子会话（返回码 0=已开启）
//   CloneDesktop.exe -enable      开启子会话（需管理员权限）
//   CloneDesktop.exe -disable     关闭子会话（需管理员权限）
// 日志路径：%LOCALAPPDATA%\yes-nk\clone-desktop\viewer.log
//
// 仅使用 C# 5 语法，保证 Windows 自带 .NET Framework 4.0 csc.exe 零依赖编译通过。

using System;
using System.Drawing;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Windows.Forms;

[ComImport, Guid("302D8188-0052-4807-806A-362B628F9AC5"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMsRdpExtendedSettings
{
    void put_Property([MarshalAs(UnmanagedType.BStr)] string name, ref object value);
    void get_Property([MarshalAs(UnmanagedType.BStr)] string name, out object value);
}

[ComImport, Guid("336D5562-EFA8-482E-8CB3-C5C0FC7A7DB6"), InterfaceType(ComInterfaceType.InterfaceIsIDispatch)]
public interface IMsTscAxEvents
{
    [DispId(1)] void OnConnecting();
    [DispId(2)] void OnConnected();
    [DispId(3)] void OnLoginComplete();
    [DispId(4)] void OnDisconnected(int discReason);
    [DispId(10)] void OnFatalError(int errorCode);
    [DispId(11)] void OnWarning(int warningCode);
    [DispId(22)] void OnLogonError(int lError);
}

[ClassInterface(ClassInterfaceType.None)]
public class RdpEvents : IMsTscAxEvents
{
    public int DisconnectReason = -1;
    public DateTime LoginTime = DateTime.MinValue;
    public void OnConnecting() { Program.Log("event: connecting"); }
    public void OnConnected() { Program.Log("event: connected"); }
    public void OnLoginComplete() { LoginTime = DateTime.Now; Program.Log("event: login complete"); }
    public void OnDisconnected(int discReason) { DisconnectReason = discReason; Program.Log("event: disconnected, reason " + discReason); }
    public void OnFatalError(int errorCode) { Program.Log("event: fatal error " + errorCode); }
    public void OnWarning(int warningCode) { Program.Log("event: warning " + warningCode); }
    public void OnLogonError(int lError) { Program.Log("event: logon error " + lError); }
}

// Microsoft RDP Client Control (MsTscAx)
public class RdpBox : AxHost
{
    public readonly RdpEvents Sink = new RdpEvents();
    ConnectionPointCookie cookie;

    public RdpBox() : base("8B918B82-7985-4C24-89DF-C33AD2BBFBCD") { }
    public object Ocx { get { return GetOcx(); } }

    protected override void CreateSink()
    {
        try { cookie = new ConnectionPointCookie(GetOcx(), Sink, typeof(IMsTscAxEvents)); }
        catch (Exception ex) { Program.Log("event sink failed: " + ex.Message); }
    }

    protected override void DetachSink()
    {
        try { if (cookie != null) cookie.Disconnect(); }
        catch { }
        cookie = null;
    }
}

static class Program
{
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    struct CredUiInfo
    {
        public int cbSize;
        public IntPtr hwndParent;
        public string pszMessageText;
        public string pszCaptionText;
        public IntPtr hbmBanner;
    }

    [DllImport("credui.dll", CharSet = CharSet.Unicode)]
    static extern int CredUIPromptForWindowsCredentials(ref CredUiInfo info, int authError, ref uint authPackage,
        IntPtr inBuffer, uint inBufferSize, out IntPtr outBuffer, out uint outBufferSize, ref bool save, int flags);
    [DllImport("credui.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    static extern bool CredPackAuthenticationBuffer(int flags, string userName, string password, IntPtr packed, ref int packedSize);
    [DllImport("credui.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    static extern bool CredUnPackAuthenticationBuffer(int flags, IntPtr buffer, uint bufferSize, StringBuilder userName,
        ref int userNameSize, StringBuilder domain, ref int domainSize, StringBuilder password, ref int passwordSize);

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    struct Credential
    {
        public int Flags;
        public int Type;
        public string TargetName;
        public string Comment;
        public long LastWritten;
        public int CredentialBlobSize;
        public IntPtr CredentialBlob;
        public int Persist;
        public int AttributeCount;
        public IntPtr Attributes;
        public string TargetAlias;
        public string UserName;
    }

    [DllImport("advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    static extern bool CredWrite(ref Credential credential, int flags);
    [DllImport("advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    static extern bool CredRead(string target, int type, int flags, out IntPtr credential);
    [DllImport("advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    static extern bool CredDelete(string target, int type, int flags);
    [DllImport("advapi32.dll")]
    static extern void CredFree(IntPtr buffer);

    const int CreduiwinGeneric = 0x1, CreduiwinCheckbox = 0x2, CredPackGenericCredentials = 0x4;
    const int CredTypeGeneric = 1, CredPersistLocalMachine = 2;
    const string SavedTarget = "yes-nk/clone-desktop";

    [DllImport("wtsapi32.dll", SetLastError = true)]
    static extern bool WTSEnableChildSessions(bool enable);
    [DllImport("wtsapi32.dll")]
    static extern bool WTSIsChildSessionsEnabled(out bool enabled);
    [DllImport("wtsapi32.dll")]
    static extern bool WTSGetChildSessionId(out uint sessionId);

    const string Title = "YES-NK 桌面分身";
    // 固定 1920x1080 基准桌面分辨率，外层窗口按 SmartSizing 自动等比缩放显示
    const int DesktopWidth = 1920, DesktopHeight = 1080;
    const int MaxReconnects = 3;

    static readonly string dataDir = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "yes-nk", "clone-desktop");
    static readonly string logPath = Path.Combine(dataDir, "viewer.log");
    static readonly string launchResultPath = Path.Combine(dataDir, "launch-result.txt");
    static readonly string endRequestPath = Path.Combine(dataDir, "end-request.txt");

    internal static void Log(string message)
    {
        try { File.AppendAllText(logPath, DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss.fff") + " " + message + Environment.NewLine); }
        catch { }
    }

    static bool Enabled()
    {
        bool enabled;
        return WTSIsChildSessionsEnabled(out enabled) && enabled;
    }

    static int RdpPort()
    {
        try
        {
            using (var key = Microsoft.Win32.Registry.LocalMachine.OpenSubKey(@"SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp"))
            {
                object value = key == null ? null : key.GetValue("PortNumber");
                if (value is int && (int)value > 0) return (int)value;
            }
        }
        catch (Exception ex) { Log("rdp port: " + ex.Message); }
        return 3389;
    }

    static string DefaultAccount()
    {
        try
        {
            using (var key = Microsoft.Win32.Registry.CurrentUser.OpenSubKey(@"Software\Microsoft\IdentityCRL\UserExtendedProperties"))
            {
                if (key != null)
                    foreach (string name in key.GetSubKeyNames())
                        if (name.Contains("@")) return "MicrosoftAccount\\" + name;
            }
        }
        catch { }
        return Environment.MachineName + "\\" + Environment.UserName;
    }

    static bool ReadSaved(out string account, out string password)
    {
        account = password = null;
        IntPtr pointer;
        if (!CredRead(SavedTarget, CredTypeGeneric, 0, out pointer)) return false;
        try
        {
            var credential = (Credential)Marshal.PtrToStructure(pointer, typeof(Credential));
            if (credential.CredentialBlobSize <= 0 || string.IsNullOrEmpty(credential.UserName)) return false;
            account = credential.UserName;
            password = Marshal.PtrToStringUni(credential.CredentialBlob, credential.CredentialBlobSize / 2);
            return true;
        }
        finally { CredFree(pointer); }
    }

    static void Save(string account, string password)
    {
        IntPtr blob = Marshal.StringToCoTaskMemUni(password);
        try
        {
            var credential = new Credential
            {
                Type = CredTypeGeneric,
                TargetName = SavedTarget,
                Comment = "YES-NK 桌面分身登录凭据",
                CredentialBlobSize = password.Length * 2,
                CredentialBlob = blob,
                Persist = CredPersistLocalMachine,
                UserName = account,
            };
            Log(CredWrite(ref credential, 0) ? "password saved in Credential Manager" : "saving password failed, error " + Marshal.GetLastWin32Error());
        }
        finally { Marshal.ZeroFreeCoTaskMemUnicode(blob); }
    }

    internal static void ForgetSaved()
    {
        if (CredDelete(SavedTarget, CredTypeGeneric, 0)) Log("saved password deleted");
    }

    // Windows 原生凭据弹窗（纯账号密码，无 PIN，带“记住我的凭据”）
    static bool PromptCredentials(IntPtr parent, ref string account, out string password, out bool save)
    {
        password = null;
        save = false;
        var info = new CredUiInfo
        {
            hwndParent = parent,
            pszCaptionText = Title,
            pszMessageText = "请输入本机 Windows 账户密码（微软账户请填微软密码，不是 PIN）。\n勾选「记住我的凭据」后下次开启分身无需再输入。",
        };
        info.cbSize = Marshal.SizeOf(typeof(CredUiInfo));
        int inSize = 0;
        IntPtr inBuffer = IntPtr.Zero;
        CredPackAuthenticationBuffer(CredPackGenericCredentials, account, "", IntPtr.Zero, ref inSize);
        if (inSize > 0)
        {
            inBuffer = Marshal.AllocCoTaskMem(inSize);
            if (!CredPackAuthenticationBuffer(CredPackGenericCredentials, account, "", inBuffer, ref inSize))
            {
                Marshal.FreeCoTaskMem(inBuffer);
                inBuffer = IntPtr.Zero;
                inSize = 0;
            }
        }
        uint package = 0;
        IntPtr outBuffer;
        uint outSize;
        bool saveBox = true;
        int result = CredUIPromptForWindowsCredentials(ref info, 0, ref package, inBuffer, (uint)inSize,
            out outBuffer, out outSize, ref saveBox, CreduiwinGeneric | CreduiwinCheckbox);
        if (inBuffer != IntPtr.Zero) Marshal.FreeCoTaskMem(inBuffer);
        if (result != 0)
        {
            Log("sign-in box closed, result " + result);
            return false;
        }
        try
        {
            var user = new StringBuilder(1024);
            var domain = new StringBuilder(1024);
            var secret = new StringBuilder(1024);
            int userSize = user.Capacity, domainSize = domain.Capacity, secretSize = secret.Capacity;
            if (!CredUnPackAuthenticationBuffer(0, outBuffer, outSize, user, ref userSize, domain, ref domainSize, secret, ref secretSize))
            {
                Log("sign-in box: unpack failed, error " + Marshal.GetLastWin32Error());
                return false;
            }
            if (user.Length > 0)
                account = domain.Length > 0 ? domain + "\\" + user : user.ToString();
            password = secret.ToString();
            save = saveBox;
            if (password.Length == 0)
            {
                Log("sign-in box: empty password");
                MessageBox.Show(
                    "桌面分身必须使用带密码的 Windows 账户登录。\n" +
                    "若当前账户未设置密码，请先到系统「设置 > 账户 > 登录选项 > 密码」添加一个密码。",
                    Title, MessageBoxButtons.OK, MessageBoxIcon.Warning);
            }
            return password.Length > 0;
        }
        finally
        {
            Marshal.Copy(new byte[outSize], 0, outBuffer, (int)outSize);
            Marshal.FreeCoTaskMem(outBuffer);
        }
    }

    static void SignOutChild(bool wait = false)
    {
        uint id;
        if (!WTSGetChildSessionId(out id) || id == 0 || id == uint.MaxValue)
        {
            Log("sign out: no child session");
            return;
        }
        Log("signing out child session " + id);
        var info = new System.Diagnostics.ProcessStartInfo("logoff", id.ToString()) { UseShellExecute = false, CreateNoWindow = true };
        using (var logoff = System.Diagnostics.Process.Start(info))
            if (wait && logoff != null) logoff.WaitForExit(15000);
    }

    static void OpenOnDesktop(string uri)
    {
        System.Threading.Thread.Sleep(3000);
        Log("opening on the desktop: " + uri);
        System.Diagnostics.Process.Start("explorer.exe", "\"" + uri + "\"");
    }

    static string AskClose(Form owner, bool canMove)
    {
        string result = "cancel";
        using (var box = new Form
        {
            Text = Title, FormBorderStyle = FormBorderStyle.FixedDialog, StartPosition = FormStartPosition.CenterParent,
            MinimizeBox = false, MaximizeBox = false, ShowInTaskbar = false, ClientSize = new Size(440, 130),
        })
        {
            box.Controls.Add(new Label
            {
                Text = "要关闭桌面分身吗？分身里的游戏和脚本也会一起关闭。\n" +
                       (canMove ? "选择「搬回桌面」会在关闭分身后，在主桌面重新打开游戏。" : ""),
                Location = new Point(16, 14), Size = new Size(410, 56),
            });
            int x = 16;
            Action<string, string> add = (label, value) =>
            {
                var button = new Button { Text = label, Location = new Point(x, 84), Size = new Size(130, 30) };
                button.Click += delegate { result = value; box.Close(); };
                box.Controls.Add(button);
                x += 140;
            };
            add("直接关掉", "end");
            if (canMove) add("搬回桌面", "move");
            add("取消", "cancel");
            box.ShowDialog(owner);
        }
        Log("close asked: " + result);
        return result;
    }

    static bool IsElevated()
    {
        using (var identity = System.Security.Principal.WindowsIdentity.GetCurrent())
            return new System.Security.Principal.WindowsPrincipal(identity).IsInRole(
                System.Security.Principal.WindowsBuiltInRole.Administrator);
    }

    static void WriteLaunchResult(string text)
    {
        Log("launch: " + text);
        try { File.WriteAllText(launchResultPath, text, new UTF8Encoding(false)); }
        catch (Exception ex) { Log("launch result not written: " + ex.Message); }
    }

    // 通过一次性 Windows 计划任务 (TASK_RUN_USE_SESSION_ID) 在子会话中免密启动 YES-NK
    static string LaunchInClone(string exe, string arguments, string directory)
    {
        uint id;
        if (!WTSGetChildSessionId(out id) || id == 0 || id == uint.MaxValue)
            return "failed 找不到桌面分身会话";
        foreach (var process in System.Diagnostics.Process.GetProcessesByName(Path.GetFileNameWithoutExtension(exe)))
        {
            using (process)
            {
                try { if (process.SessionId == (int)id) return "running " + process.Id; }
                catch { }
            }
        }
        Type type = Type.GetTypeFromProgID("Schedule.Service");
        if (type == null) return "failed 本机缺少任务计划程序服务";
        string taskName = "yes-nk-clone-desktop-launch-" + Guid.NewGuid().ToString("N");
        string user;
        using (var identity = System.Security.Principal.WindowsIdentity.GetCurrent())
            user = identity.Name;
        dynamic scheduler = Activator.CreateInstance(type);
        scheduler.Connect();
        dynamic folder = scheduler.GetFolder("\\");
        dynamic task = scheduler.NewTask(0);
        task.RegistrationInfo.Author = "yes-nk";
        task.RegistrationInfo.Description = "YES-NK 桌面分身：在子会话中启动工具（运行后立即删除）";
        task.Settings.Enabled = true;
        task.Settings.Hidden = true;
        task.Settings.AllowDemandStart = true;
        task.Settings.DisallowStartIfOnBatteries = false;
        task.Settings.StopIfGoingOnBatteries = false;
        task.Settings.ExecutionTimeLimit = "PT0S";
        task.Settings.Priority = 4;
        task.Principal.UserId = user;
        task.Principal.LogonType = 3;  // TASK_LOGON_INTERACTIVE_TOKEN
        task.Principal.RunLevel = IsElevated() ? 1 : 0;  // 提权启动，适配国服 WeGame/ACE
        dynamic action = task.Actions.Create(0);  // TASK_ACTION_EXEC
        action.Path = exe;
        action.Arguments = arguments ?? "";
        if (!string.IsNullOrEmpty(directory)) action.WorkingDirectory = directory;
        bool registered = false;
        try
        {
            dynamic registeredTask = folder.RegisterTaskDefinition(taskName, task, 2, user, null, 3, null);
            registered = true;
            registeredTask.RunEx(null, 4, (int)id, null);  // TASK_RUN_USE_SESSION_ID
            return "started";
        }
        finally
        {
            if (registered)
            {
                try { folder.DeleteTask(taskName, 0); }
                catch (Exception ex) { Log("launch task not deleted: " + ex.Message); }
            }
        }
    }

    static readonly string StartupListFile = Path.Combine(dataDir, "startup-programs.txt");
    static readonly string StartupTaskListFile = Path.Combine(dataDir, "startup-tasks.txt");
    static int sweepGeneration;

    static void StartStartupSweep(uint session)
    {
        var programs = new System.Collections.Generic.HashSet<string>(StringComparer.OrdinalIgnoreCase);
        try
        {
            foreach (string line in File.ReadAllLines(StartupListFile))
                if (line.Trim().Length > 0) programs.Add(line.Trim());
        }
        catch (Exception ex) { Log("startup sweep: no list (" + ex.Message + ")"); return; }

        var taskPrograms = new System.Collections.Generic.HashSet<string>(StringComparer.OrdinalIgnoreCase);
        try
        {
            foreach (string line in File.ReadAllLines(StartupTaskListFile))
                if (line.Trim().Length > 0) taskPrograms.Add(line.Trim());
        }
        catch { }
        if (programs.Count == 0 && taskPrograms.Count == 0) return;

        int generation = System.Threading.Interlocked.Increment(ref sweepGeneration);
        var closed = new System.Collections.Generic.HashSet<int>();
        Func<int, int> parentOf = delegate (int pid)
        {
            try
            {
                using (var searcher = new System.Management.ManagementObjectSearcher(
                    "SELECT ParentProcessId FROM Win32_Process WHERE ProcessId=" + pid))
                    foreach (System.Management.ManagementObject row in searcher.Get())
                        return Convert.ToInt32(row["ParentProcessId"]);
            }
            catch { }
            return -1;
        };
        Func<int, string> commandLineOf = delegate (int pid)
        {
            try
            {
                using (var searcher = new System.Management.ManagementObjectSearcher(
                    "SELECT CommandLine FROM Win32_Process WHERE ProcessId=" + pid))
                    foreach (System.Management.ManagementObject row in searcher.Get())
                        return Convert.ToString(row["CommandLine"]) ?? "";
            }
            catch { }
            return "";
        };
        Func<int, bool, bool> startedBySignIn = delegate (int parent, bool fromTask)
        {
            if (parent <= 0) return false;
            lock (closed) if (closed.Contains(parent)) return true;
            try
            {
                using (var p = System.Diagnostics.Process.GetProcessById(parent))
                {
                    string name = p.ProcessName.ToLowerInvariant();
                    if (name == "explorer" || name == "userinit") return true;
                    return fromTask && (name == "svchost" || name == "taskhostw");
                }
            }
            catch { return false; }
        };
        Action<int, int> check = delegate (int pid, int parent)
        {
            try
            {
                using (var process = System.Diagnostics.Process.GetProcessById(pid))
                {
                    if (process.SessionId != (int)session) return;
                    bool child;
                    lock (closed) child = closed.Contains(parent);
                    string path = process.MainModule.FileName;
                    bool fromTask = taskPrograms.Contains(path);
                    if (!child && !programs.Contains(path) && !fromTask) return;
                    if (parent < 0) parent = parentOf(pid);
                    if (!startedBySignIn(parent, fromTask)) return;
                    if (fromTask && commandLineOf(pid).Contains("://")) return;
                    lock (closed) closed.Add(pid);
                    Log("startup sweep: closing " + Path.GetFileName(path) + " in session " + session);
                    var kill = new System.Diagnostics.ProcessStartInfo("taskkill", "/T /F /PID " + pid)
                    { UseShellExecute = false, CreateNoWindow = true };
                    System.Diagnostics.Process.Start(kill);
                }
            }
            catch { }
        };
        var thread = new System.Threading.Thread(delegate ()
        {
            System.Management.ManagementEventWatcher watcher = null;
            try
            {
                watcher = new System.Management.ManagementEventWatcher(
                    new System.Management.WqlEventQuery("SELECT * FROM Win32_ProcessStartTrace"));
                watcher.EventArrived += delegate (object sender, System.Management.EventArrivedEventArgs e)
                {
                    try
                    {
                        if (Convert.ToInt32(e.NewEvent["SessionID"]) == (int)session)
                            check(Convert.ToInt32(e.NewEvent["ProcessID"]),
                                  Convert.ToInt32(e.NewEvent["ParentProcessID"]));
                    }
                    catch { }
                };
                watcher.Start();
            }
            catch (Exception ex)
            {
                if (watcher != null) { try { watcher.Dispose(); } catch { } }
                watcher = null;
                Log("startup sweep: start trace unavailable (" + ex.Message + "), polling creations");
                try
                {
                    watcher = new System.Management.ManagementEventWatcher(
                        new System.Management.WqlEventQuery(
                            "SELECT * FROM __InstanceCreationEvent WITHIN 1 WHERE TargetInstance ISA 'Win32_Process'"));
                    watcher.EventArrived += delegate (object sender, System.Management.EventArrivedEventArgs e)
                    {
                        try
                        {
                            var target = (System.Management.ManagementBaseObject)e.NewEvent["TargetInstance"];
                            if (Convert.ToInt32(target["SessionId"]) == (int)session)
                                check(Convert.ToInt32(target["ProcessId"]),
                                      Convert.ToInt32(target["ParentProcessId"]));
                        }
                        catch { }
                    };
                    watcher.Start();
                }
                catch (Exception ex2)
                {
                    watcher = null;
                    Log("startup sweep: no process-start events (" + ex2.Message + ")");
                }
            }
            foreach (var process in System.Diagnostics.Process.GetProcesses())
            {
                int pid = process.Id;
                process.Dispose();
                check(pid, -1);
            }
            DateTime start = DateTime.Now;
            while (generation == sweepGeneration && (DateTime.Now - start).TotalSeconds < 300)
                System.Threading.Thread.Sleep(1000);
            if (watcher != null)
            {
                try { watcher.Stop(); watcher.Dispose(); } catch { }
            }
            Log("startup sweep: done");
        });
        thread.IsBackground = true;
        thread.Start();
    }

    static void LaunchOnce(string exe, string arguments, string directory, NotifyIcon tray)
    {
        string result;
        try { result = LaunchInClone(exe, arguments, directory); }
        catch (Exception ex) { result = "failed " + ex.Message; }
        WriteLaunchResult(result);
        if (result.StartsWith("failed") && tray != null)
            tray.ShowBalloonTip(8000, Title, "未能在分身内自动拉起 YES-NK，请在分身窗口中手动打开。", ToolTipIcon.Warning);
    }

    static readonly int[] ConnectFailures = { 260, 264, 516, 520, 772, 1028, 1288, 2308 };

    internal static bool IsConnectFailure(int reason)
    {
        return Array.IndexOf(ConnectFailures, reason) >= 0;
    }

    static string CheckRemoteDesktopService()
    {
        try
        {
            using (var service = new System.Management.ManagementObject("Win32_Service.Name='TermService'"))
            {
                service.Get();
                string mode = Convert.ToString(service["StartMode"]);
                string state = Convert.ToString(service["State"]);
                Log("remote desktop service: " + mode + ", " + state);
                if (mode == "Disabled")
                    return "Windows 的「远程桌面服务 (TermService)」已被禁用，桌面分身依赖此服务。\n" +
                           "请回到 YES-NK 桌面分身页面点击「帮我打开」。";
                if (state != "Running")
                {
                    object code = service.InvokeMethod("StartService", null);
                    Log("start remote desktop service => " + code);
                    for (int i = 0; i < 20; i++)
                    {
                        System.Threading.Thread.Sleep(500);
                        service.Get();
                        if (Convert.ToString(service["State"]) == "Running") break;
                    }
                    Log("remote desktop service now " + service["State"]);
                }
            }
        }
        catch (System.Management.ManagementException ex)
        {
            Log("remote desktop service: " + ex.ErrorCode + " " + ex.Message);
            if (ex.ErrorCode == System.Management.ManagementStatus.NotFound)
                return "本机缺少 Windows「远程桌面服务 (TermService)」，无法使用桌面分身。\n" +
                       "常见于精简版 Windows 或系统优化工具精简了服务，请改用主桌面后台模式。";
        }
        catch (Exception ex) { Log("remote desktop service check failed: " + ex.Message); }
        return null;
    }

    static string Describe(dynamic ocx, int reason)
    {
        if (reason < 0) return "（未收到断开原因）";
        uint extended = 0;
        try { extended = (uint)(int)ocx.ExtendedDisconnectReason; } catch { }
        try
        {
            string text = ocx.GetErrorDescription((uint)reason, extended);
            return text + "（代码 " + reason + "／" + extended + "）";
        }
        catch (Exception ex) { return "代码 " + reason + "／" + extended + "（" + ex.Message + "）"; }
    }

    [STAThread]
    static int Main(string[] args)
    {
        Directory.CreateDirectory(dataDir);
        string command = args.Length > 0 ? args[0] : "";
        if (command == "-check")
        {
            bool enabled = Enabled();
            Log("check: child sessions enabled = " + enabled);
            return enabled ? 0 : 1;
        }
        if (command == "-enable" || command == "-disable")
        {
            bool want = command == "-enable";
            bool ok = WTSEnableChildSessions(want);
            int error = Marshal.GetLastWin32Error();
            bool enabled = Enabled();
            Log("WTSEnableChildSessions(" + want + ") => " + ok + " (error " + error + "), enabled now = " + enabled);
            return enabled == want ? 0 : 1;
        }

        string account = null, launchExe = null, launchArgs = "", launchDir = null, moveUri = null;
        for (int i = 0; i < args.Length; i += 2)
        {
            if (i + 1 >= args.Length)
            {
                MessageBox.Show("参数缺少值：" + args[i], Title);
                return 2;
            }
            if (args[i] == "-user") account = args[i + 1];
            else if (args[i] == "-launch") launchExe = args[i + 1];
            else if (args[i] == "-args") launchArgs = args[i + 1];
            else if (args[i] == "-cwd") launchDir = args[i + 1];
            else if (args[i] == "-move") moveUri = args[i + 1];
            else
            {
                MessageBox.Show("无法识别的参数：" + args[i], Title);
                return 2;
            }
        }

        bool firstInstance;
        using (var single = new System.Threading.Mutex(true, "Local\\yes-nk-clone-desktop", out firstInstance))
        {
            if (!firstInstance)
            {
                if (launchExe != null) LaunchOnce(launchExe, launchArgs, launchDir, null);
                else MessageBox.Show("YES-NK 桌面分身已经在运行（请查看右下角系统托盘图标）。", Title);
                return 1;
            }
            return Run(account, launchExe, launchArgs, launchDir, moveUri);
        }
    }

    static int Run(string account, string launchExe, string launchArgs, string launchDir, string moveUri)
    {
        if (!Enabled())
        {
            MessageBox.Show("桌面分身尚未开启。\n请先在 YES-NK 点击「第一次设定」（或运行 tools\\clone_desktop\\setup.ps1）。", Title);
            return 1;
        }
        Application.EnableVisualStyles();
        string serviceProblem = CheckRemoteDesktopService();
        if (serviceProblem != null)
        {
            if (launchExe != null) WriteLaunchResult("failed 远程桌面服务不可用");
            MessageBox.Show(serviceProblem, Title, MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return 1;
        }

        string password;
        bool fromSaved = false, saveAfterLogin = false;
        string savedAccount;
        if (ReadSaved(out savedAccount, out password))
        {
            fromSaved = true;
            if (account == null) account = savedAccount;
        }
        else
        {
            if (account == null) account = DefaultAccount();
            if (!PromptCredentials(IntPtr.Zero, ref account, out password, out saveAfterLogin))
            {
                if (launchExe != null) WriteLaunchResult("failed 未输入登录密码");
                return 1;
            }
        }

        Log("viewer start, user " + account + (fromSaved ? " (saved password)" : ""));
        var form = new Form { Text = Title + "（连接中）", Width = 1360, Height = 820 };
        Icon icon = SystemIcons.Application;
        try { icon = Icon.ExtractAssociatedIcon(Application.ExecutablePath); } catch { }
        form.Icon = icon;
        form.Show();
        form.Activate();
        var tray = new NotifyIcon { Icon = icon, Visible = true, Text = Title };

        var rdp = new RdpBox { Dock = DockStyle.Fill };
        form.Controls.Add(rdp);
        rdp.CreateControl();
        dynamic ocx = rdp.Ocx;

        bool closingForReal = false;
        bool wantReconnect = true;
        bool everConnected = false;
        bool launchPending = launchExe != null;
        DateTime connectedSince = DateTime.MaxValue;
        int failedReconnects = 0;
        int last = -1;
        DateTime lastAttempt = DateTime.Now;
        var timer = new Timer { Interval = 2000 };

        Action connect = delegate
        {
            lastAttempt = DateTime.Now;
            try
            {
                ocx.Server = "localhost";
                ocx.UserName = account;
                ocx.AdvancedSettings2.ClearTextPassword = password;
                try { ocx.AdvancedSettings2.RDPPort = RdpPort(); } catch { }
                ocx.DesktopWidth = DesktopWidth;
                ocx.DesktopHeight = DesktopHeight;
                try { ocx.AdvancedSettings2.SmartSizing = true; } catch { }
                try { ocx.AdvancedSettings2.GrabFocusOnConnect = false; } catch { }
                try { ocx.ColorDepth = 32; } catch { }
                try { ocx.SecuredSettings2.KeyboardHookMode = 1; } catch { }
                try { ocx.AdvancedSettings7.EnableCredSspSupport = true; } catch { }
                object yes = true;
                ((IMsRdpExtendedSettings)rdp.Ocx).put_Property("ConnectToChildSession", ref yes);
                Log("connecting");
                ocx.Connect();
            }
            catch (Exception ex) { Log("connect failed: " + ex.Message); }
        };

        Action show = delegate { form.Show(); form.WindowState = FormWindowState.Normal; form.Activate(); };
        var menu = new ContextMenuStrip();
        menu.Items.Add("显示窗口", null, delegate { show(); });
        menu.Items.Add("重新连接", null, delegate
        {
            Log("manual reconnect");
            failedReconnects = 0;
            wantReconnect = true;
            lastAttempt = DateTime.MinValue;
            try { if ((int)ocx.Connected != 0) ocx.Disconnect(); } catch { }
        });
        menu.Items.Add("结束分身（游戏和脚本一起关）", null, delegate { form.Close(); });
        tray.ContextMenuStrip = menu;
        tray.DoubleClick += delegate { show(); };

        form.FormClosing += (sender, e) =>
        {
            if (!closingForReal)
            {
                string answer = e.CloseReason == CloseReason.UserClosing ? AskClose(form, moveUri != null) : "end";
                if (answer == "cancel") { e.Cancel = true; return; }
                try
                {
                    SignOutChild(answer == "move");
                    if (answer == "move") OpenOnDesktop(moveUri);
                }
                catch (Exception ex) { Log("close failed: " + ex.Message); }
            }
            wantReconnect = false;
            timer.Stop();
            tray.Visible = false;
            if (launchPending) { launchPending = false; WriteLaunchResult("failed 分身窗口在登录完成前关闭"); }
            Log("viewer closing (" + e.CloseReason + ")");
        };

        timer.Tick += delegate
        {
            try
            {
                if (!closingForReal && File.Exists(endRequestPath))
                {
                    string asked = "end";
                    try { asked = File.ReadAllText(endRequestPath).Trim(); } catch { }
                    try { File.Delete(endRequestPath); } catch { }
                    bool move = asked == "move" && moveUri != null;
                    Log("end asked by tool in clone: " + asked);
                    closingForReal = true;
                    try
                    {
                        SignOutChild(move);
                        if (move) OpenOnDesktop(moveUri);
                    }
                    catch (Exception ex) { Log("close failed: " + ex.Message); }
                    form.Close();
                    return;
                }

                int state = (int)ocx.Connected;  // 0 disconnected, 1 connected, 2 connecting
                if (state != last)
                {
                    string extra = "";
                    if (state == 0)
                        extra = " " + Describe(ocx, rdp.Sink.DisconnectReason);
                    if (state == 1)
                    {
                        uint id;
                        if (WTSGetChildSessionId(out id)) extra = " child_session=" + id;
                    }
                    Log("state " + last + " -> " + state + extra);
                    last = state;
                    form.Text = Title + (state == 1 ? "（最小化也会继续跑）" : state == 2 ? "（连接中）" : "（未连接）");
                }

                if (state == 1)
                {
                    failedReconnects = 0;
                    everConnected = true;
                    if (saveAfterLogin)
                    {
                        saveAfterLogin = false;
                        Save(account, password);
                    }
                    if (connectedSince == DateTime.MaxValue)
                    {
                        connectedSince = DateTime.Now;
                        uint sweepSession;
                        if (WTSGetChildSessionId(out sweepSession)) StartStartupSweep(sweepSession);
                    }
                    DateTime login = rdp.Sink.LoginTime;
                    if (launchPending && ((login != DateTime.MinValue && (DateTime.Now - login).TotalSeconds >= 3)
                                          || (DateTime.Now - connectedSince).TotalSeconds >= 20))
                    {
                        launchPending = false;
                        LaunchOnce(launchExe, launchArgs, launchDir, tray);
                    }
                }
                else connectedSince = DateTime.MaxValue;

                if (state != 0 || !wantReconnect || (DateTime.Now - lastAttempt).TotalSeconds < 5) return;
                if (!everConnected)
                {
                    wantReconnect = false;
                    int reason = rdp.Sink.DisconnectReason;
                    string why = Describe(ocx, reason);
                    Log("first logon failed, not retrying: " + why);
                    if (IsConnectFailure(reason))
                    {
                        if (launchPending) { launchPending = false; WriteLaunchResult("failed noconnect " + reason); }
                        MessageBox.Show(
                            "连不上桌面分身（不是密码问题）。\n\nWindows 返回说明：" + why +
                            "\n\n请按顺序排查：" +
                            "\n1. 关闭此窗口和 YES-NK，重新打开后再点一次「在桌面分身跑」。" +
                            "\n2. 重启电脑后再试（首次开启子会话常需重启后生效）。" +
                            "\n3. 若安装过 RDP Wrapper 或用过系统精简工具，Windows「远程桌面服务」可能受损。",
                            Title, MessageBoxButtons.OK, MessageBoxIcon.Warning);
                        closingForReal = true;
                        form.Close();
                        return;
                    }
                    if (fromSaved) ForgetSaved();
                    if (launchPending) { launchPending = false; WriteLaunchResult("failed 登录桌面分身失败"); }
                    MessageBox.Show(
                        "登录桌面分身失败。\n\nWindows 返回说明：" + why +
                        "\n\n常见原因：" +
                        "\n1. 需输入 Windows 账户密码（微软账户填微软密码），不能填 PIN。" +
                        "\n2. 若只用过 PIN/人脸开机，请按 Win+L 选择钥匙图标用密码登录一次电脑。" +
                        "\n3. 若系统开启了「仅允许 Windows Hello 登录」，请在 YES-NK 桌面分身页点击「帮我关掉」。" +
                        (fromSaved ? "\n（原记住的凭据已失效并自动清除，下次将重新询问密码。）" : ""),
                        Title, MessageBoxButtons.OK, MessageBoxIcon.Warning);
                    closingForReal = true;
                    form.Close();
                    return;
                }

                if (failedReconnects >= MaxReconnects)
                {
                    wantReconnect = false;
                    Log("giving up after " + failedReconnects + " reconnects");
                    tray.ShowBalloonTip(5000, Title, "分身重连失败，请右键托盘图标点击「重新连接」或关闭后重开。", ToolTipIcon.Warning);
                    return;
                }
                failedReconnects++;
                Log("reconnect " + failedReconnects);
                connect();
            }
            catch (Exception ex) { Log("poll failed: " + ex.Message); }
        };

        try { File.Delete(endRequestPath); } catch { }
        timer.Start();

        connect();
        Application.Run(form);
        tray.Visible = false;
        Log("viewer exit");
        return 0;
    }
}
