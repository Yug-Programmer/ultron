using System;
using System.Diagnostics;
using System.IO;
using System.Management;
using System.Runtime.InteropServices;
using System.Text.RegularExpressions;
using System.Threading;
using System.Windows;

namespace Ultron.Net.Tools
{
    public static class WindowsAutomator
    {
        [DllImport("user32.dll")]
        private static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, UIntPtr dwExtraInfo);

        private const byte VK_CONTROL = 0x11;
        private const byte VK_A = 0x41;
        private const byte VK_C = 0x43;
        private const byte VK_V = 0x56;
        private const byte VK_Z = 0x5A;
        private const byte VK_Y = 0x59;
        private const byte VK_S = 0x53;
        private const byte VK_BACK = 0x08;
        private const byte VK_SHIFT = 0x10;
        private const byte VK_HOME = 0x24;
        private const uint KEYEVENTF_KEYUP = 0x0002;

        public static string TypeInActiveEditor(string text)
        {
            try
            {
                if (string.IsNullOrWhiteSpace(text))
                    return "No text provided to type.";

                Application.Current.Dispatcher.Invoke(() =>
                {
                    Clipboard.SetText(text);
                });

                Thread.Sleep(50);
                // Ctrl + V
                keybd_event(VK_CONTROL, 0, 0, UIntPtr.Zero);
                keybd_event(VK_V, 0, 0, UIntPtr.Zero);
                keybd_event(VK_V, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
                keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);

                return $"Typed: '{text}'.";
            }
            catch (Exception ex)
            {
                return $"Failed to type: {ex.Message}";
            }
        }

        public static string ReplaceInActiveEditor(string find, string replace)
        {
            try
            {
                // Select all (Ctrl + A)
                keybd_event(VK_CONTROL, 0, 0, UIntPtr.Zero);
                keybd_event(VK_A, 0, 0, UIntPtr.Zero);
                keybd_event(VK_A, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
                keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
                Thread.Sleep(50);

                // Copy (Ctrl + C)
                keybd_event(VK_CONTROL, 0, 0, UIntPtr.Zero);
                keybd_event(VK_C, 0, 0, UIntPtr.Zero);
                keybd_event(VK_C, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
                keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
                Thread.Sleep(80);

                string content = "";
                Application.Current.Dispatcher.Invoke(() =>
                {
                    if (Clipboard.ContainsText())
                        content = Clipboard.GetText();
                });

                if (string.IsNullOrEmpty(content))
                    return "No text was detected in the active window.";

                if (!Regex.IsMatch(content, Regex.Escape(find), RegexOptions.IgnoreCase))
                    return $"Could not find '{find}' in the active window.";

                string updated = Regex.Replace(content, Regex.Escape(find), replace, RegexOptions.IgnoreCase);

                Application.Current.Dispatcher.Invoke(() =>
                {
                    Clipboard.SetText(updated);
                });

                Thread.Sleep(50);
                // Paste (Ctrl + V)
                keybd_event(VK_CONTROL, 0, 0, UIntPtr.Zero);
                keybd_event(VK_V, 0, 0, UIntPtr.Zero);
                keybd_event(VK_V, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
                keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);

                return $"Replaced '{find}' with '{replace}' in active document, sir.";
            }
            catch (Exception ex)
            {
                return $"Failed to replace text: {ex.Message}";
            }
        }

        public static string ClearActiveEditor()
        {
            try
            {
                // Ctrl + A
                keybd_event(VK_CONTROL, 0, 0, UIntPtr.Zero);
                keybd_event(VK_A, 0, 0, UIntPtr.Zero);
                keybd_event(VK_A, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
                keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
                Thread.Sleep(50);

                // Backspace
                keybd_event(VK_BACK, 0, 0, UIntPtr.Zero);
                keybd_event(VK_BACK, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);

                return "Cleared content in active window, sir.";
            }
            catch (Exception ex)
            {
                return $"Failed to clear window: {ex.Message}";
            }
        }

        public static string DeleteLastWord()
        {
            try
            {
                // Ctrl + Backspace
                keybd_event(VK_CONTROL, 0, 0, UIntPtr.Zero);
                keybd_event(VK_BACK, 0, 0, UIntPtr.Zero);
                keybd_event(VK_BACK, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
                keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);

                return "Deleted word, sir.";
            }
            catch (Exception ex)
            {
                return $"Failed to delete word: {ex.Message}";
            }
        }

        public static string DeleteLine()
        {
            try
            {
                // Shift + Home
                keybd_event(VK_SHIFT, 0, 0, UIntPtr.Zero);
                keybd_event(VK_HOME, 0, 0, UIntPtr.Zero);
                keybd_event(VK_HOME, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
                keybd_event(VK_SHIFT, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
                Thread.Sleep(30);

                // Backspace
                keybd_event(VK_BACK, 0, 0, UIntPtr.Zero);
                keybd_event(VK_BACK, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);

                return "Deleted line, sir.";
            }
            catch (Exception ex)
            {
                return $"Failed to delete line: {ex.Message}";
            }
        }

        public static string Undo()
        {
            keybd_event(VK_CONTROL, 0, 0, UIntPtr.Zero);
            keybd_event(VK_Z, 0, 0, UIntPtr.Zero);
            keybd_event(VK_Z, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
            keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
            return "Undone, sir.";
        }

        public static string Redo()
        {
            keybd_event(VK_CONTROL, 0, 0, UIntPtr.Zero);
            keybd_event(VK_Y, 0, 0, UIntPtr.Zero);
            keybd_event(VK_Y, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
            keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
            return "Redone, sir.";
        }

        public static string SaveDocument()
        {
            keybd_event(VK_CONTROL, 0, 0, UIntPtr.Zero);
            keybd_event(VK_S, 0, 0, UIntPtr.Zero);
            keybd_event(VK_S, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
            keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
            return "Document saved, sir.";
        }

        public static string LaunchApplication(string appName)
        {
            string clean = appName.ToLower().Trim();
            string command = clean;

            if (clean.Contains("notepad") || clean.Contains("note")) command = "notepad.exe";
            else if (clean.Contains("word") && !clean.Contains("pad")) command = "winword.exe";
            else if (clean.Contains("excel")) command = "excel.exe";
            else if (clean.Contains("powerpoint")) command = "powerpnt.exe";
            else if (clean.Contains("calculator") || clean.Contains("calc")) command = "calc.exe";
            else if (clean.Contains("task manager")) command = "taskmgr.exe";
            else if (clean.Contains("chrome")) command = "chrome.exe";
            else if (clean.Contains("edge")) command = "msedge.exe";

            try
            {
                Process.Start(new ProcessStartInfo(command) { UseShellExecute = true });
                return $"Opening {appName}, sir.";
            }
            catch
            {
                try
                {
                    Process.Start(new ProcessStartInfo("cmd.exe", $"/c start \"\" \"{appName}\"") { CreateNoWindow = true });
                    return $"Opening {appName}, sir.";
                }
                catch (Exception ex)
                {
                    return $"Could not open {appName}: {ex.Message}";
                }
            }
        }

        public static string OpenFolderOrDrive(string query)
        {
            string q = query.ToLower().Trim();
            string targetPath = "";

            if (q.Contains("c drive") || q.Contains("local disk c") || q.Contains("disk c")) targetPath = @"C:\";
            else if (q.Contains("y drive") || q.Contains("new volume y") || q.Contains("volume y")) targetPath = @"Y:\";
            else if (q.Contains("program files")) targetPath = @"C:\Program Files";
            else if (q.Contains("windows")) targetPath = @"C:\Windows";
            else if (q.Contains("users")) targetPath = @"C:\Users";
            else if (q.Contains("ultron")) targetPath = @"Y:\Ultron";
            else if (q.Contains("downloads")) targetPath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "Downloads");
            else if (q.Contains("documents")) targetPath = Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments);
            else if (q.Contains("desktop")) targetPath = Environment.GetFolderPath(Environment.SpecialFolder.Desktop);

            if (string.IsNullOrEmpty(targetPath) || !Directory.Exists(targetPath))
            {
                return LaunchApplication(query);
            }

            try
            {
                Process.Start(new ProcessStartInfo("explorer.exe", $"\"{targetPath}\"") { UseShellExecute = true });
                return $"Opening {Path.GetFileName(targetPath) ?? targetPath}, sir.";
            }
            catch (Exception ex)
            {
                return $"Failed to open folder: {ex.Message}";
            }
        }

        public static string FindAndModifyFile(string filename, string instruction)
        {
            string[] searchRoots = new[]
            {
                @"Y:\Ultron",
                Environment.GetFolderPath(Environment.SpecialFolder.Desktop),
                Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "Downloads")
            };

            string? foundFile = null;
            foreach (var root in searchRoots)
            {
                if (!Directory.Exists(root)) continue;
                var direct = Path.Combine(root, filename);
                if (File.Exists(direct)) { foundFile = direct; break; }

                try
                {
                    var files = Directory.GetFiles(root, $"*{filename}*", SearchOption.TopDirectoryOnly);
                    if (files.Length > 0) { foundFile = files[0]; break; }
                }
                catch { }
            }

            if (foundFile == null)
            {
                foundFile = Path.Combine(@"Y:\Ultron", filename);
            }

            try
            {
                File.AppendAllText(foundFile, $"\n{instruction}\n");
                return $"Updated {Path.GetFileName(foundFile)} with your instruction, sir.";
            }
            catch (Exception ex)
            {
                return $"Failed to update file: {ex.Message}";
            }
        }

        public static string DeleteFileOnDisk(string filename)
        {
            string[] searchRoots = new[]
            {
                @"Y:\Ultron",
                Environment.GetFolderPath(Environment.SpecialFolder.Desktop),
                Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "Downloads")
            };

            foreach (var root in searchRoots)
            {
                if (!Directory.Exists(root)) continue;
                try
                {
                    var files = Directory.GetFiles(root, $"*{filename}*", SearchOption.TopDirectoryOnly);
                    if (files.Length > 0)
                    {
                        File.Delete(files[0]);
                        return $"Successfully deleted {Path.GetFileName(files[0])}, sir.";
                    }
                }
                catch { }
            }

            return $"I could not locate '{filename}' to delete, sir.";
        }

        public static string GetSystemVitals()
        {
            try
            {
                var driveC = new DriveInfo("C");
                double freeGb = driveC.AvailableFreeSpace / (1024.0 * 1024.0 * 1024.0);

                int batteryPercent = 100;
                try
                {
                    using var searcher = new ManagementObjectSearcher("SELECT EstimatedChargeRemaining FROM Win32_Battery");
                    foreach (ManagementObject obj in searcher.Get())
                    {
                        batteryPercent = Convert.ToInt32(obj["EstimatedChargeRemaining"]);
                        break;
                    }
                }
                catch { }

                return $"C Drive has {freeGb:F1} GB free. Battery is at {batteryPercent}%, sir.";
            }
            catch (Exception ex)
            {
                return $"Vitals query notice: {ex.Message}";
            }
        }
    }
}
