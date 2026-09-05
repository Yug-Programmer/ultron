using System;
using System.Windows;
using System.Windows.Input;
using System.Windows.Media;
using Ultron.Shared.Config;
using Ultron.Net.Services;
using Ultron.Net.Tools;

namespace Ultron.Net
{
    public partial class MainWindow : Window
    {
        private readonly UltronConfig _config;
        private readonly Orchestrator _orchestrator;
        private bool _isMuted = false;

        public MainWindow()
        {
            InitializeComponent();

            MouseDown += (s, e) =>
            {
                if (e.ChangedButton == MouseButton.Left)
                    DragMove();
            };

            _config = UltronConfig.Load();
            _orchestrator = new Orchestrator(_config);

            _orchestrator.OnSubtitlesChanged += (userText, ultronText) =>
            {
                Dispatcher.Invoke(() =>
                {
                    UserSpeechText.Text = $"User: \"{userText}\"";
                    UltronReplyText.Text = $"Ultron: \"{ultronText}\"";
                });
            };

            _orchestrator.OnStateChanged += (state) =>
            {
                Dispatcher.Invoke(() =>
                {
                    StateText.Text = state;
                    if (state == "LISTENING")
                    {
                        StatusDot.Fill = new SolidColorBrush(Color.FromRgb(0x00, 0xFF, 0xCC));
                    }
                    else if (state == "PROCESSING")
                    {
                        StatusDot.Fill = new SolidColorBrush(Color.FromRgb(0xFF, 0xAA, 0x00));
                    }
                });
            };

            Loaded += (s, e) =>
            {
                _orchestrator.Start();
            };

            Closed += (s, e) =>
            {
                _orchestrator.Dispose();
            };
        }

        private void CloseButton_Click(object sender, RoutedEventArgs e)
        {
            Close();
        }

        private void TestVitals_Click(object sender, RoutedEventArgs e)
        {
            string vitals = WindowsAutomator.GetSystemVitals();
            UserSpeechText.Text = "User: [Manual Check]";
            UltronReplyText.Text = $"Ultron: \"{vitals}\"";
        }

        private void ToggleMic_Click(object sender, RoutedEventArgs e)
        {
            if (!_isMuted)
            {
                _orchestrator.Stop();
                _isMuted = true;
                ToggleMicBtn.Content = "Unmute";
                ToggleMicBtn.Foreground = new SolidColorBrush(Color.FromRgb(0x00, 0xFF, 0xCC));
                ToggleMicBtn.BorderBrush = new SolidColorBrush(Color.FromRgb(0x00, 0xFF, 0xCC));
                StateText.Text = "MUTED";
                StatusDot.Fill = new SolidColorBrush(Color.FromRgb(0x88, 0x88, 0x88));
            }
            else
            {
                _orchestrator.Start();
                _isMuted = false;
                ToggleMicBtn.Content = "Mute";
                ToggleMicBtn.Foreground = new SolidColorBrush(Color.FromRgb(0xFF, 0x33, 0x66));
                ToggleMicBtn.BorderBrush = new SolidColorBrush(Color.FromRgb(0xFF, 0x33, 0x66));
            }
        }
    }
}