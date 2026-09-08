using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Ultron.Shared.Memory;

namespace Ultron.Net.Services
{
    public class ScreenWatcher : IDisposable
    {
        [DllImport("user32.dll")]
        private static extern IntPtr GetForegroundWindow();

        [DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)]
        private static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);

        [DllImport("user32.dll", SetLastError = true)]
        private static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);

        private readonly MemoryService _memory;
        private readonly CancellationTokenSource _cts = new();
        private Thread? _watcherThread;

        private IntPtr _lastHwnd = IntPtr.Zero;
        private string _lastProcessName = "";
        private string _lastWindowTitle = "";
        private DateTime _windowFocusStartTime = DateTime.UtcNow;
        private DateTime _lastPeriodicFlush = DateTime.UtcNow;

        public string CurrentActiveApp => _lastProcessName;
        public string CurrentWindowTitle => _lastWindowTitle;
        public TimeSpan CurrentFocusDuration => DateTime.UtcNow - _windowFocusStartTime;

        public event Action<string, string>? OnWindowChanged;
        public event Action<string, string>? OnErrorDialogDetected;

        public ScreenWatcher(MemoryService? memory = null)
        {
            _memory = memory ?? MemoryService.Instance;
        }

        public void Start()
        {
            if (_watcherThread != null && _watcherThread.IsAlive)
                return;

            _watcherThread = new Thread(RunWatcherLoop)
            {
                IsBackground = true,
                Name = "Ultron_ScreenWatcher_247",
                Priority = ThreadPriority.Lowest // Ensures zero impact on user activities/gaming
            };
            _watcherThread.Start();
            Console.WriteLine("[ScreenWatcher] 24/7 background screen monitoring started.");
        }

        public void Stop()
        {
            try
            {
                _cts.Cancel();
                _watcherThread?.Join(500);
            }
            catch { }
        }

        private void RunWatcherLoop()
        {
            while (!_cts.IsCancellationRequested)
            {
                try
                {
                    CheckActiveWindow();
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"[ScreenWatcher] Watcher loop notice: {ex.Message}");
                }

                try
                {
                    Thread.Sleep(2500);
                }
                catch (ThreadInterruptedException)
                {
                    break;
                }
            }

            // Flush final window session on exit
            FlushCurrentSession();
        }

        private void CheckActiveWindow()
        {
            IntPtr hwnd = GetForegroundWindow();
            if (hwnd == IntPtr.Zero)
                return;

            string title = GetWindowTitle(hwnd);
            string procName = GetProcessName(hwnd);

            // If window changed
            if (hwnd != _lastHwnd || procName != _lastProcessName || title != _lastWindowTitle)
            {
                FlushCurrentSession();

                _lastHwnd = hwnd;
                _lastProcessName = procName;
                _lastWindowTitle = title;
                _windowFocusStartTime = DateTime.UtcNow;
                _lastPeriodicFlush = DateTime.UtcNow;

                OnWindowChanged?.Invoke(procName, title);

                // Detect error or hung windows
                if (title.Contains("Not Responding", StringComparison.OrdinalIgnoreCase) ||
                    title.Contains("Fatal Error", StringComparison.OrdinalIgnoreCase) ||
                    title.Contains("Crash Reporter", StringComparison.OrdinalIgnoreCase))
                {
                    OnErrorDialogDetected?.Invoke(procName, title);
                }
            }
            else
            {
                // If staying in the same window for more than 60 seconds, flush intermediate chunk so data is never lost
                if ((DateTime.UtcNow - _lastPeriodicFlush).TotalSeconds >= 60)
                {
                    int chunkSec = (int)(DateTime.UtcNow - _lastPeriodicFlush).TotalSeconds;
                    _lastPeriodicFlush = DateTime.UtcNow;
                    if (!string.IsNullOrEmpty(_lastProcessName) && chunkSec > 0)
                    {
                        Task.Run(() => _memory.LogScreenActivityAsync(_lastProcessName, _lastWindowTitle, chunkSec));
                    }
                }
            }
        }

        private void FlushCurrentSession()
        {
            if (string.IsNullOrEmpty(_lastProcessName) && string.IsNullOrEmpty(_lastWindowTitle))
                return;

            int durationSec = (int)(DateTime.UtcNow - _lastPeriodicFlush).TotalSeconds;
            if (durationSec >= 2)
            {
                string proc = _lastProcessName;
                string title = _lastWindowTitle;
                Task.Run(() => _memory.LogScreenActivityAsync(proc, title, durationSec));
            }
        }

        private static string GetWindowTitle(IntPtr hwnd)
        {
            const int nChars = 256;
            var sb = new StringBuilder(nChars);
            if (GetWindowText(hwnd, sb, nChars) > 0)
            {
                return sb.ToString().Trim();
            }
            return "";
        }

        private static string GetProcessName(IntPtr hwnd)
        {
            try
            {
                GetWindowThreadProcessId(hwnd, out uint pid);
                if (pid != 0)
                {
                    using var proc = Process.GetProcessById((int)pid);
                    return proc.ProcessName;
                }
            }
            catch { }
            return "";
        }

        public void Dispose()
        {
            Stop();
            _cts.Dispose();
        }
    }
}
