using System;
using System.IO;
using System.Windows;

namespace Ultron.Net;

/// <summary>
/// Interaction logic for App.xaml
/// </summary>
public partial class App : Application
{
    public App()
    {
        DispatcherUnhandledException += (s, e) =>
        {
            File.AppendAllText("crash.log", $"[UI Exception] {DateTime.UtcNow}: {e.Exception}\n");
            MessageBox.Show($"UI Exception: {e.Exception.Message}", "Ultron Startup Error", MessageBoxButton.OK, MessageBoxImage.Error);
        };

        AppDomain.CurrentDomain.UnhandledException += (s, e) =>
        {
            File.AppendAllText("crash.log", $"[AppDomain Exception] {DateTime.UtcNow}: {e.ExceptionObject}\n");
        };
    }
}

