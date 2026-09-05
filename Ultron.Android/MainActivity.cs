using System;
using System.Collections.Generic;
using Android.App;
using Android.Content;
using Android.Content.PM;
using Android.OS;
using Android.Widget;
using Ultron.Android.Services;

namespace Ultron.Android
{
    [Activity(Label = "Ultron AI", MainLauncher = true)]
    public class MainActivity : Activity
    {
        private const int PermissionRequestCode = 200;
        private TextView? _statusText;
        private Button? _toggleBtn;
        private bool _isServiceRunning = false;

        protected override void OnCreate(Bundle? savedInstanceState)
        {
            base.OnCreate(savedInstanceState);
            SetContentView(Resource.Layout.activity_main);

            _statusText = FindViewById<TextView>(Resource.Id.status_text);
            _toggleBtn = FindViewById<Button>(Resource.Id.toggle_button);

            CheckAndRequestPermissions();

            _toggleBtn?.SetOnClickListener(new ButtonClickListener(() =>
            {
                if (!_isServiceRunning)
                {
                    StartVoiceService();
                }
                else
                {
                    StopVoiceService();
                }
            }));
        }

        private void CheckAndRequestPermissions()
        {
            var permissionsToRequest = new List<string>();

            if (CheckSelfPermission(global::Android.Manifest.Permission.RecordAudio) != Permission.Granted)
            {
                permissionsToRequest.Add(global::Android.Manifest.Permission.RecordAudio);
            }

            if (Build.VERSION.SdkInt >= BuildVersionCodes.Tiramisu)
            {
                if (CheckSelfPermission(global::Android.Manifest.Permission.PostNotifications) != Permission.Granted)
                {
                    permissionsToRequest.Add(global::Android.Manifest.Permission.PostNotifications);
                }
            }

            if (permissionsToRequest.Count > 0)
            {
                RequestPermissions(permissionsToRequest.ToArray(), PermissionRequestCode);
            }
            else
            {
                StartVoiceService();
            }
        }

        public override void OnRequestPermissionsResult(int requestCode, string[] permissions, Permission[] grantResults)
        {
            base.OnRequestPermissionsResult(requestCode, permissions, grantResults);
            if (requestCode == PermissionRequestCode)
            {
                StartVoiceService();
            }
        }

        private void StartVoiceService()
        {
            var intent = new Intent(this, typeof(AndroidVoiceService));
            if (Build.VERSION.SdkInt >= BuildVersionCodes.O)
            {
                StartForegroundService(intent);
            }
            else
            {
                StartService(intent);
            }

            _isServiceRunning = true;
            if (_statusText != null) _statusText.Text = "Ultron Status: ACTIVE (Listening...)";
            if (_toggleBtn != null) _toggleBtn.Text = "Deactivate Ultron";
        }

        private void StopVoiceService()
        {
            var intent = new Intent(this, typeof(AndroidVoiceService));
            StopService(intent);

            _isServiceRunning = false;
            if (_statusText != null) _statusText.Text = "Ultron Status: STOPPED";
            if (_toggleBtn != null) _toggleBtn.Text = "Activate Ultron";
        }

        private class ButtonClickListener : Java.Lang.Object, global::Android.Views.View.IOnClickListener
        {
            private readonly Action _action;
            public ButtonClickListener(Action action) => _action = action;
            public void OnClick(global::Android.Views.View? v) => _action();
        }
    }
}