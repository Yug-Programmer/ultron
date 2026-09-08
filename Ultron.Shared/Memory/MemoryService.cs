using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Threading.Tasks;
using Microsoft.Data.Sqlite;

namespace Ultron.Shared.Memory
{
    public class ScreenActivityRecord
    {
        public int Id { get; set; }
        public DateTime Timestamp { get; set; }
        public string ProcessName { get; set; } = "";
        public string WindowTitle { get; set; } = "";
        public int DurationSeconds { get; set; }
    }

    public class UserFactRecord
    {
        public string Key { get; set; } = "";
        public string Value { get; set; } = "";
        public double Confidence { get; set; }
        public DateTime LastUpdated { get; set; }
    }

    public class MemoryService
    {
        private readonly string _dbPath;
        private readonly string _connectionString;
        private static MemoryService? _instance;
        private static readonly object _lock = new();

        public static MemoryService Instance
        {
            get
            {
                if (_instance == null)
                {
                    lock (_lock)
                    {
                        _instance ??= new MemoryService();
                    }
                }
                return _instance;
            }
        }

        public MemoryService(string? customDbPath = null)
        {
            if (!string.IsNullOrEmpty(customDbPath))
            {
                _dbPath = customDbPath;
            }
            else
            {
                string dir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Ultron");
                Directory.CreateDirectory(dir);
                _dbPath = Path.Combine(dir, "ultron_memory.db");
            }

            _connectionString = new SqliteConnectionStringBuilder
            {
                DataSource = _dbPath,
                Mode = SqliteOpenMode.ReadWriteCreate,
                Cache = SqliteCacheMode.Shared
            }.ToString();

            InitializeDatabase();
        }

        private void InitializeDatabase()
        {
            try
            {
                using var conn = new SqliteConnection(_connectionString);
                conn.Open();

                using var walCmd = conn.CreateCommand();
                walCmd.CommandText = "PRAGMA journal_mode = WAL;";
                walCmd.ExecuteNonQuery();

                string schema = @"
                    CREATE TABLE IF NOT EXISTS UserInteractions (
                        Id INTEGER PRIMARY KEY AUTOINCREMENT,
                        Timestamp TEXT NOT NULL,
                        UserSpeech TEXT NOT NULL,
                        Action TEXT NOT NULL,
                        Reply TEXT NOT NULL,
                        Context TEXT
                    );

                    CREATE TABLE IF NOT EXISTS ScreenTimeline (
                        Id INTEGER PRIMARY KEY AUTOINCREMENT,
                        Timestamp TEXT NOT NULL,
                        ProcessName TEXT NOT NULL,
                        WindowTitle TEXT NOT NULL,
                        DurationSeconds INTEGER NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS UserFacts (
                        Id INTEGER PRIMARY KEY AUTOINCREMENT,
                        Key TEXT UNIQUE NOT NULL,
                        Value TEXT NOT NULL,
                        Confidence REAL NOT NULL DEFAULT 1.0,
                        LastUpdated TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS FileHistory (
                        Id INTEGER PRIMARY KEY AUTOINCREMENT,
                        Timestamp TEXT NOT NULL,
                        FilePath TEXT NOT NULL,
                        ActionType TEXT NOT NULL
                    );

                    CREATE INDEX IF NOT EXISTS idx_timeline_ts ON ScreenTimeline(Timestamp);
                    CREATE INDEX IF NOT EXISTS idx_interactions_ts ON UserInteractions(Timestamp);
                ";

                using var cmd = conn.CreateCommand();
                cmd.CommandText = schema;
                cmd.ExecuteNonQuery();
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[MemoryService] Init warning: {ex.Message}");
            }
        }

        public async Task LogInteractionAsync(string userSpeech, string action, string reply, string? context = null)
        {
            try
            {
                using var conn = new SqliteConnection(_connectionString);
                await conn.OpenAsync();

                using var cmd = conn.CreateCommand();
                cmd.CommandText = @"
                    INSERT INTO UserInteractions (Timestamp, UserSpeech, Action, Reply, Context)
                    VALUES ($ts, $speech, $action, $reply, $context);
                ";
                cmd.Parameters.AddWithValue("$ts", DateTime.UtcNow.ToString("o"));
                cmd.Parameters.AddWithValue("$speech", userSpeech ?? "");
                cmd.Parameters.AddWithValue("$action", action ?? "");
                cmd.Parameters.AddWithValue("$reply", reply ?? "");
                cmd.Parameters.AddWithValue("$context", context ?? (object)DBNull.Value);

                await cmd.ExecuteNonQueryAsync();
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[MemoryService] LogInteraction error: {ex.Message}");
            }
        }

        public async Task LogScreenActivityAsync(string processName, string windowTitle, int durationSeconds)
        {
            if (string.IsNullOrWhiteSpace(processName) && string.IsNullOrWhiteSpace(windowTitle))
                return;

            if (durationSeconds <= 0)
                return;

            try
            {
                using var conn = new SqliteConnection(_connectionString);
                await conn.OpenAsync();

                using var cmd = conn.CreateCommand();
                cmd.CommandText = @"
                    INSERT INTO ScreenTimeline (Timestamp, ProcessName, WindowTitle, DurationSeconds)
                    VALUES ($ts, $pname, $title, $dur);
                ";
                cmd.Parameters.AddWithValue("$ts", DateTime.UtcNow.ToString("o"));
                cmd.Parameters.AddWithValue("$pname", processName.Trim());
                cmd.Parameters.AddWithValue("$title", windowTitle.Trim());
                cmd.Parameters.AddWithValue("$dur", durationSeconds);

                await cmd.ExecuteNonQueryAsync();
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[MemoryService] LogScreenActivity error: {ex.Message}");
            }
        }

        public async Task LogFileActivityAsync(string filePath, string actionType)
        {
            try
            {
                using var conn = new SqliteConnection(_connectionString);
                await conn.OpenAsync();

                using var cmd = conn.CreateCommand();
                cmd.CommandText = @"
                    INSERT INTO FileHistory (Timestamp, FilePath, ActionType)
                    VALUES ($ts, $file, $action);
                ";
                cmd.Parameters.AddWithValue("$ts", DateTime.UtcNow.ToString("o"));
                cmd.Parameters.AddWithValue("$file", filePath);
                cmd.Parameters.AddWithValue("$action", actionType);

                await cmd.ExecuteNonQueryAsync();
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[MemoryService] LogFileActivity error: {ex.Message}");
            }
        }

        public async Task LearnUserFactAsync(string key, string value, double confidence = 1.0)
        {
            if (string.IsNullOrWhiteSpace(key) || string.IsNullOrWhiteSpace(value))
                return;

            try
            {
                using var conn = new SqliteConnection(_connectionString);
                await conn.OpenAsync();

                using var cmd = conn.CreateCommand();
                cmd.CommandText = @"
                    INSERT INTO UserFacts (Key, Value, Confidence, LastUpdated)
                    VALUES ($key, $val, $conf, $ts)
                    ON CONFLICT(Key) DO UPDATE SET
                        Value = excluded.Value,
                        Confidence = excluded.Confidence,
                        LastUpdated = excluded.LastUpdated;
                ";
                cmd.Parameters.AddWithValue("$key", key.Trim());
                cmd.Parameters.AddWithValue("$val", value.Trim());
                cmd.Parameters.AddWithValue("$conf", confidence);
                cmd.Parameters.AddWithValue("$ts", DateTime.UtcNow.ToString("o"));

                await cmd.ExecuteNonQueryAsync();
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[MemoryService] LearnUserFact error: {ex.Message}");
            }
        }

        public async Task<List<UserFactRecord>> GetUserFactsAsync()
        {
            var facts = new List<UserFactRecord>();
            try
            {
                using var conn = new SqliteConnection(_connectionString);
                await conn.OpenAsync();

                using var cmd = conn.CreateCommand();
                cmd.CommandText = "SELECT Key, Value, Confidence, LastUpdated FROM UserFacts ORDER BY LastUpdated DESC LIMIT 50;";

                using var reader = await cmd.ExecuteReaderAsync();
                while (await reader.ReadAsync())
                {
                    facts.Add(new UserFactRecord
                    {
                        Key = reader.GetString(0),
                        Value = reader.GetString(1),
                        Confidence = reader.GetDouble(2),
                        LastUpdated = DateTime.TryParse(reader.GetString(3), out var dt) ? dt : DateTime.UtcNow
                    });
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[MemoryService] GetUserFacts error: {ex.Message}");
            }
            return facts;
        }

        public async Task<List<ScreenActivityRecord>> QueryRecentScreenTimelineAsync(int minutes = 120)
        {
            var list = new List<ScreenActivityRecord>();
            try
            {
                using var conn = new SqliteConnection(_connectionString);
                await conn.OpenAsync();

                var cutoff = DateTime.UtcNow.AddMinutes(-minutes).ToString("o");

                using var cmd = conn.CreateCommand();
                cmd.CommandText = @"
                    SELECT Id, Timestamp, ProcessName, WindowTitle, DurationSeconds
                    FROM ScreenTimeline
                    WHERE Timestamp >= $cutoff
                    ORDER BY Timestamp DESC
                    LIMIT 200;
                ";
                cmd.Parameters.AddWithValue("$cutoff", cutoff);

                using var reader = await cmd.ExecuteReaderAsync();
                while (await reader.ReadAsync())
                {
                    list.Add(new ScreenActivityRecord
                    {
                        Id = reader.GetInt32(0),
                        Timestamp = DateTime.TryParse(reader.GetString(1), out var dt) ? dt : DateTime.UtcNow,
                        ProcessName = reader.GetString(2),
                        WindowTitle = reader.GetString(3),
                        DurationSeconds = reader.GetInt32(4)
                    });
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[MemoryService] QueryRecentScreenTimeline error: {ex.Message}");
            }
            return list;
        }

        public async Task<string> FormatTimelineSummaryAsync(int hours = 12)
        {
            try
            {
                var timeline = await QueryRecentScreenTimelineAsync(hours * 60);
                if (timeline.Count == 0)
                    return "No screen activity recorded in the specified timeframe, sir.";

                var processDurations = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
                var recentTitles = new List<string>();

                foreach (var item in timeline)
                {
                    if (!processDurations.ContainsKey(item.ProcessName))
                        processDurations[item.ProcessName] = 0;
                    processDurations[item.ProcessName] += item.DurationSeconds;

                    if (recentTitles.Count < 4 && !string.IsNullOrWhiteSpace(item.WindowTitle) && !recentTitles.Contains(item.WindowTitle))
                    {
                        recentTitles.Add($"{item.ProcessName}: \"{item.WindowTitle}\"");
                    }
                }

                var sb = new StringBuilder();
                sb.AppendLine($"Summary of recent activity in the last {hours} hours:");

                foreach (var kvp in processDurations)
                {
                    int minutes = kvp.Value / 60;
                    int seconds = kvp.Value % 60;
                    if (minutes > 0)
                        sb.AppendLine($"• {kvp.Key}: {minutes}m {seconds}s");
                    else
                        sb.AppendLine($"• {kvp.Key}: {seconds}s");
                }

                if (recentTitles.Count > 0)
                {
                    sb.AppendLine("Recent windows focused:");
                    foreach (var title in recentTitles)
                    {
                        sb.AppendLine($"  - {title}");
                    }
                }

                return sb.ToString().Trim();
            }
            catch (Exception ex)
            {
                return $"Error generating timeline summary: {ex.Message}";
            }
        }

        public async Task<string> GetPersonalizedContextSummaryAsync()
        {
            try
            {
                var sb = new StringBuilder();

                // 1. Facts
                var facts = await GetUserFactsAsync();
                if (facts.Count > 0)
                {
                    sb.AppendLine("Learned User Facts & Preferences:");
                    foreach (var f in facts)
                    {
                        sb.AppendLine($"- {f.Key}: {f.Value}");
                    }
                }

                // 2. Recent Screen Timeline (last 30 minutes)
                var recentActivity = await QueryRecentScreenTimelineAsync(30);
                if (recentActivity.Count > 0)
                {
                    sb.AppendLine("\nRecent Screen & App Context (Past 30 mins):");
                    var set = new HashSet<string>();
                    foreach (var act in recentActivity)
                    {
                        string desc = $"{act.ProcessName} ('{act.WindowTitle}')";
                        if (set.Add(desc))
                        {
                            sb.AppendLine($"- Active app: {desc}");
                            if (set.Count >= 5) break;
                        }
                    }
                }

                return sb.ToString().Trim();
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[MemoryService] ContextSummary error: {ex.Message}");
                return string.Empty;
            }
        }
    }
}
