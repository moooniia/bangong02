using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Media.Imaging;
using Microsoft.UI.Xaml.Input;
using System;
using System.Diagnostics;
using System.Collections.Generic;
using System.Globalization;
using System.Numerics;
using System.Threading;
using System.Linq;
using Microsoft.UI.Xaml.Controls.Primitives;
using System.IO;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Threading.Tasks;
using Windows.ApplicationModel;
using Windows.Storage.Pickers;
using Windows.Storage;
using Windows.System;
using WinRT.Interop;

namespace InvoiceToolbox.WinUI;

public sealed partial class MainPage : UserControl
{
    public UIElement TitleBarElement => AppTitleBar;
    private JsonArray _records = new();
    private JsonObject? _selected;
    private Process? _worker;
    private double _zoom = 1;
    private bool _dragging;
    private Windows.Foundation.Point _dragStart;
    private double _startX;
    private double _startY;
    private bool _leftPanelVisible = true;
    private bool _reviewPanelVisible = true;
    private bool _wideReview;
    private bool _pendingOnly;
    private int _previewRequestId;
    private int _renderGeneration;
    private readonly Dictionary<string, string> _previewCache = new();
    private readonly SemaphoreSlim _previewLock = new(1, 1);
    private Process? _previewWorker;
    private Dictionary<string, string> _archiveLookup = new(StringComparer.OrdinalIgnoreCase);
    private readonly double[] _columnWidths = { 190, 170, 220, 170, 105, 95, 85, 95, 65, 135, 110, 105, 90, 105, 105, 80 };
    private readonly List<Grid> _renderedRowGrids = new();
    private readonly string[] _columnTitles = { "公司抬头", "购买方税号", "销售方", "销售方税号", "开票日期", "不含税额", "税额", "价税合计", "税率", "发票类型", "发票号码", "业务分类", "月份归档", "源文件", "归档文件", "审核状态" };
    private const string UpdateManifestUrl = "https://www.bangong02.com/invoice-toolbox-latest.json";
    private JsonObject? _latestUpdate;
    private string _latestVersion = "";
    private bool _updateAvailable;
    private bool _ignoreUpdateThisSession;

    public MainPage()
    {
        InitializeComponent();
        InputPathText.Text = "未选择";
        ArchivePathText.Text = "未选择";
        LoadCategories();
        PopulateExportFieldLists();
        BuildTableHeader();
        SizeChanged += OnPageSizeChanged;
        WarmPreviewWorker();
        _ = WarmPreviewBackendAsync();
        _ = CheckForUpdatesAsync();
    }

    private void PopulateExportFieldLists()
    {
        AddFieldOptions(NameFieldsList, new[] { ("buyer_name", "购买方抬头"), ("seller_name", "销售方名称"), ("invoice_no", "发票号码"), ("invoice_date", "开票日期"), ("total_amount", "价税合计"), ("category", "业务分类") }, new[] { "buyer_name", "invoice_no", "invoice_date", "total_amount" });
        AddFieldOptions(ReportFieldsList, new[] { ("row_id", "序号"), ("archive_month", "归档月份"), ("category", "业务分类"), ("buyer_name", "购买方抬头"), ("buyer_tax", "购买方税号"), ("seller_name", "销售方名称"), ("seller_tax", "销售方税号"), ("invoice_date", "开票日期"), ("pretax_amount", "不含税金额"), ("tax_amount", "税额"), ("total_amount", "价税合计"), ("tax_rate", "税率"), ("invoice_type", "发票类型"), ("invoice_no", "发票号码"), ("line_items", "商品/服务"), ("original_name", "原文件名"), ("archived_name", "新文件名"), ("original_path", "原文件链接"), ("archived_path", "归档文件链接") }, null);
    }

    private static void AddFieldOptions(ListView list, IEnumerable<(string Key, string Title)> fields, IEnumerable<string>? defaults)
    {
        var selected = defaults == null ? null : new HashSet<string>(defaults);
        foreach (var field in fields)
        {
            var row = new Grid { ColumnSpacing = 8, Padding = new Thickness(2, 3, 2, 3), Tag = field.Key };
            row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(24) }); row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            var handle = new FontIcon { Glyph = "\uE700", FontSize = 12, Opacity = 0.55, VerticalAlignment = VerticalAlignment.Center };
            var check = new CheckBox { Content = field.Title, Tag = field.Key, IsChecked = selected == null || selected.Contains(field.Key), HorizontalAlignment = HorizontalAlignment.Stretch };
            Grid.SetColumn(check, 1); row.Children.Add(handle); row.Children.Add(check); list.Items.Add(row);
        }
    }

    private IEnumerable<string> SelectedFieldKeys(ListView list)
    {
        foreach (var row in list.Items.OfType<Grid>())
            if (row.Children.OfType<CheckBox>().FirstOrDefault() is { IsChecked: true, Tag: string key }) yield return key;
    }

    private void BuildTableHeader()
    {
        TableHeaderGrid.Children.Clear(); TableHeaderGrid.ColumnDefinitions.Clear(); TableHeaderGrid.ColumnSpacing = 0;
        for (var i = 0; i < _columnWidths.Length; i++)
        {
            var index = i; var definition = new ColumnDefinition { Width = new GridLength(_columnWidths[i]) }; TableHeaderGrid.ColumnDefinitions.Add(definition);
            var title = new TextBlock { Text = _columnTitles[i], Foreground = new Microsoft.UI.Xaml.Media.SolidColorBrush(Windows.UI.Color.FromArgb(255, 255, 255, 255)), HorizontalAlignment = HorizontalAlignment.Center, TextAlignment = TextAlignment.Center, VerticalAlignment = VerticalAlignment.Center };
            var titleFrame = new Border { Child = title, BorderBrush = new Microsoft.UI.Xaml.Media.SolidColorBrush(Windows.UI.Color.FromArgb(120, 132, 139, 151)), BorderThickness = i == _columnWidths.Length - 1 ? new Thickness(0) : new Thickness(0, 0, 1, 0), Margin = new Thickness(0, -3, 0, -3), Padding = new Thickness(0, 3, 0, 3) };
            Grid.SetColumn(titleFrame, i); TableHeaderGrid.Children.Add(titleFrame);
            if (i == _columnWidths.Length - 1) continue;
            var splitter = new Thumb { Width = 10, HorizontalAlignment = HorizontalAlignment.Right, Background = new Microsoft.UI.Xaml.Media.SolidColorBrush(Windows.UI.Color.FromArgb(24, 255, 255, 255)) };
            ToolTipService.SetToolTip(splitter, "拖动调整列宽");
            splitter.DragDelta += (_, e) =>
            {
                _columnWidths[index] = Math.Max(60, _columnWidths[index] + e.HorizontalChange);
                definition.Width = new GridLength(_columnWidths[index]);
                foreach (var row in _renderedRowGrids)
                {
                    row.ColumnDefinitions[index].Width = new GridLength(_columnWidths[index]);
                    row.MinWidth = _columnWidths.Sum();
                }
                TableHeaderGrid.MinWidth = _columnWidths.Sum();
            };
            Grid.SetColumn(splitter, i); Canvas.SetZIndex(splitter, 5); TableHeaderGrid.Children.Add(splitter);
        }
        TableHeaderGrid.MinWidth = _columnWidths.Sum();
    }

    private void OnThemeClick(object sender, RoutedEventArgs e) { RootLayout.RequestedTheme = RootLayout.RequestedTheme == ElementTheme.Dark ? ElementTheme.Light : ElementTheme.Dark; var dark = RootLayout.RequestedTheme == ElementTheme.Dark; SunThemeIcon.Opacity = dark ? 0.35 : 1; MoonThemeIcon.Opacity = dark ? 1 : 0.35; BuildTableHeader(); RenderRows(_pendingOnly, false); }

    private void OnInteractiveEnter(object sender, PointerRoutedEventArgs e)
    {
        if (sender is UIElement element) { element.Translation = new Vector3(0, -2, 0); element.Scale = new Vector3(1.025f, 1.025f, 1); }
    }

    private void OnInteractiveExit(object sender, PointerRoutedEventArgs e)
    {
        if (sender is UIElement element) { element.Translation = Vector3.Zero; element.Scale = Vector3.One; }
    }

    private void OnCommandPressed(object sender, PointerRoutedEventArgs e)
    {
        if (sender is UIElement element) { element.Translation = new Vector3(0, 1, 0); element.Scale = new Vector3(0.97f, 0.97f, 1); }
    }

    private void OnCommandReleased(object sender, PointerRoutedEventArgs e)
    {
        if (sender is UIElement element) { element.Translation = Vector3.Zero; element.Scale = Vector3.One; }
    }

    private void OnFolderEnter(object sender, PointerRoutedEventArgs e)
    {
        if (sender is UIElement element) { element.Translation = new Vector3(0, -2, 0); element.Scale = new Vector3(1.04f, 1.04f, 1); }
    }

    private void OnToggleLeftPanel(object sender, RoutedEventArgs e)
    {
        _leftPanelVisible = !_leftPanelVisible;
        LeftPanelColumn.Width = new GridLength(_leftPanelVisible ? 228 : 52);
        LeftPanelScroll.Visibility = _leftPanelVisible ? Visibility.Visible : Visibility.Collapsed;
        LeftPanelActions.Visibility = _leftPanelVisible ? Visibility.Visible : Visibility.Collapsed;
        LeftPanelToggleButton.HorizontalAlignment = _leftPanelVisible ? HorizontalAlignment.Left : HorizontalAlignment.Center;
        UpdatePanel.Visibility = _leftPanelVisible && _updateAvailable ? Visibility.Visible : Visibility.Collapsed;
    }

    private void OnToggleReviewPanel(object sender, RoutedEventArgs e)
    {
        _reviewPanelVisible = !_reviewPanelVisible;
        ReviewPanelColumn.Width = new GridLength(_reviewPanelVisible ? Math.Min(500, Math.Max(360, ActualWidth * 0.34)) : 0);
        ReviewPanel.Visibility = _reviewPanelVisible ? Visibility.Visible : Visibility.Collapsed;
        ReviewToggleButton.Content = _reviewPanelVisible ? "收起核对" : $"打开核对  {ReviewCountText.Text}";
    }

    private void OnPageSizeChanged(object sender, SizeChangedEventArgs e)
    {
        if (_leftPanelVisible) LeftPanelColumn.Width = new GridLength(e.NewSize.Width < 1300 ? 205 : 228);
        if (_reviewPanelVisible && !_wideReview) ReviewPanelColumn.Width = new GridLength(e.NewSize.Width < 1450 ? 380 : 500);
    }

    private void OnToggleWideReview(object sender, RoutedEventArgs e)
    {
        _wideReview = !_wideReview;
        if (!_reviewPanelVisible) { _reviewPanelVisible = true; ReviewPanel.Visibility = Visibility.Visible; }
        ReviewPanelColumn.Width = new GridLength(_wideReview ? Math.Max(620, ActualWidth - (_leftPanelVisible ? LeftPanelColumn.Width.Value : 0) - 120) : (ActualWidth < 1450 ? 380 : 500));
        ReviewToggleButton.Content = "收起核对";
    }

    private void OnAboutClick(object sender, RoutedEventArgs e) => AboutOverlay.Visibility = Visibility.Visible;
    private void OnCloseAbout(object sender, RoutedEventArgs e) => AboutOverlay.Visibility = Visibility.Collapsed;

    private async Task CheckForUpdatesAsync()
    {
        try
        {
            using var client = new HttpClient { Timeout = TimeSpan.FromSeconds(3) };
            var json = await client.GetStringAsync(UpdateManifestUrl);
            if (JsonNode.Parse(json) is not JsonObject manifest) return;
            var latest = manifest["version"]?.GetValue<string>() ?? "";
            if (string.IsNullOrWhiteSpace(latest) || !IsNewerVersion(latest, CurrentAppVersion())) return;
            ApplicationData.Current.LocalSettings.Values.Remove("IgnoredUpdateVersion");
            if (_ignoreUpdateThisSession) return;
            _latestUpdate = manifest;
            _latestVersion = latest;
            _updateAvailable = true;
            UpdateButton.Content = $"更新 {latest}";
            UpdatePanel.Visibility = _leftPanelVisible ? Visibility.Visible : Visibility.Collapsed;
        }
        catch { }
    }

    private static string CurrentAppVersion()
    {
        try
        {
            var version = Package.Current.Id.Version;
            return $"{version.Major}.{version.Minor}.{version.Build}.{version.Revision}";
        }
        catch { return "1.0.0.46"; }
    }

    private static bool IsNewerVersion(string latest, string current)
    {
        static int[] Parts(string value) => value.Trim().TrimStart('v', 'V').Split('.').Select(part => int.TryParse(part, out var n) ? n : 0).Concat(new[] { 0, 0, 0, 0 }).Take(4).ToArray();
        var l = Parts(latest); var c = Parts(current);
        for (var i = 0; i < 4; i++) { if (l[i] > c[i]) return true; if (l[i] < c[i]) return false; }
        return false;
    }

    private void OnIgnoreUpdate(object sender, RoutedEventArgs e)
    {
        _ignoreUpdateThisSession = true;
        _updateAvailable = false;
        UpdatePanel.Visibility = Visibility.Collapsed;
    }

    private async void OnUpdateClick(object sender, RoutedEventArgs e)
    {
        if (_latestUpdate == null) return;
        var url = _latestUpdate["downloadUrl"]?.GetValue<string>() ?? "";
        if (string.IsNullOrWhiteSpace(url)) { ProgressText.Text = "暂时没有可下载的更新包"; return; }
        var fullUrl = Uri.TryCreate(url, UriKind.Absolute, out var absolute) ? absolute : new Uri(new Uri("https://www.bangong02.com/"), url.TrimStart('/'));
        UpdateButton.IsEnabled = false;
        IgnoreUpdateButton.IsEnabled = false;
        ProgressText.Text = $"正在下载发票工具箱 {_latestVersion}…";
        try
        {
            using var client = new HttpClient { Timeout = TimeSpan.FromMinutes(10) };
            var bytes = await client.GetByteArrayAsync(fullUrl);
            var fileName = Path.GetFileName(fullUrl.LocalPath);
            if (string.IsNullOrWhiteSpace(fileName)) fileName = $"InvoiceToolbox.WinUI_{_latestVersion}_x64.msix";
            var targetPath = Path.Combine(ApplicationData.Current.LocalCacheFolder.Path, fileName);
            await File.WriteAllBytesAsync(targetPath, bytes);
            ProgressText.Text = "更新包已下载，正在打开安装程序…";
            var file = await StorageFile.GetFileFromPathAsync(targetPath);
            await Launcher.LaunchFileAsync(file);
        }
        catch (Exception ex)
        {
            ProgressText.Text = $"更新下载失败：{ex.Message}";
            UpdateButton.IsEnabled = true;
            IgnoreUpdateButton.IsEnabled = true;
        }
    }

    private void OnShowOverview(object sender, RoutedEventArgs e) => RenderRows();
    private void OnShowPending(object sender, RoutedEventArgs e) => RenderRows(true);
    private void OnTogglePendingOnly(object sender, RoutedEventArgs e) { _pendingOnly = !_pendingOnly; RenderRows(_pendingOnly); }
    private void OnOpenArchiveFolder(object sender, RoutedEventArgs e)
    {
        if (string.IsNullOrWhiteSpace(ArchivePathText.Text) || ArchivePathText.Text == "未选择")
        {
            ProgressText.Text = "请先选择归档文件夹";
            return;
        }
        if (!Directory.Exists(ArchivePathText.Text))
        {
            ProgressText.Text = "归档文件夹不存在，请重新选择";
            return;
        }
        Process.Start(new ProcessStartInfo("explorer.exe", $"\"{ArchivePathText.Text}\"") { UseShellExecute = true });
    }

    private async void OnChooseInputFolder(object sender, RoutedEventArgs e) => InputPathText.Text = await PickFolderAsync() ?? InputPathText.Text;
    private async void OnChooseArchiveFolder(object sender, RoutedEventArgs e) { ArchivePathText.Text = await PickFolderAsync() ?? ArchivePathText.Text; RefreshArchiveLookup(); }

    private void RefreshArchiveLookup()
    {
        _archiveLookup = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        if (!Directory.Exists(ArchivePathText.Text)) return;
        try
        {
            foreach (var path in Directory.EnumerateFiles(ArchivePathText.Text, "*.*", SearchOption.AllDirectories).Where(path => !path.EndsWith(".xlsx", StringComparison.OrdinalIgnoreCase)))
            {
                var name = Path.GetFileNameWithoutExtension(path);
                foreach (var part in name.Split('_', '-', ' ')) if (part.Length >= 8 && part.All(char.IsDigit)) _archiveLookup.TryAdd(part, path);
            }
        }
        catch { }
    }

    private static async Task<string?> PickFolderAsync()
    {
        var picker = new FolderPicker { SuggestedStartLocation = PickerLocationId.Desktop };
        picker.FileTypeFilter.Add("*");
        InitializeWithWindow.Initialize(picker, WindowNative.GetWindowHandle(MainWindow.Instance));
        return (await picker.PickSingleFolderAsync())?.Path;
    }

    private async void OnStartScan(object sender, RoutedEventArgs e)
    {
        if (!Directory.Exists(InputPathText.Text)) { ProgressText.Text = "请先选择发票文件夹"; return; }
        RecordRows.Children.Clear(); _records = new JsonArray(); ScanButton.IsEnabled = false; CancelButton.Visibility = Visibility.Visible; ScanProgress.IsIndeterminate = true; ProgressText.Text = "正在准备识别…";
        await Task.Delay(50);
        var excludeFolder = Directory.Exists(ArchivePathText.Text) ? ArchivePathText.Text : "";
        var request = JsonSerializer.Serialize(new { command = "scan", folder = InputPathText.Text, exclude_folder = excludeFolder });
        var lastRendered = 0;
        var renderClock = Stopwatch.StartNew();
        try { await RunWarmWorkerCommandAsync(request, "complete", item =>
        {
            var type = item["event"]?.GetValue<string>();
            if (type == "scan_started")
            {
                var total = item["total"]?.GetValue<int>() ?? 0; var excluded = item["excluded"]?.GetValue<int>() ?? 0;
                ScanProgress.IsIndeterminate = false; ScanProgress.Value = 0;
                ProgressText.Text = excluded > 0 ? $"已递归发现 {total} 张，跳过归档副本 {excluded} 张" : $"已递归发现 {total} 张发票";
            }
            else if (type == "progress")
            {
                ScanProgress.IsIndeterminate = false; var done = item["done"]!.GetValue<int>(); var total = item["total"]!.GetValue<int>();
                var percent = total == 0 ? 0 : done * 100.0 / total; ScanProgress.Value = percent; ProgressText.Text = $"正在识别 {done} / {total}  ·  {percent:0}%";
                if (item["record"] is JsonObject record) _records.Add(record.DeepClone());
                if (done == total || done - lastRendered >= 3 || renderClock.ElapsedMilliseconds >= 140) { RenderRows(_pendingOnly, true); lastRendered = done; renderClock.Restart(); }
            }
            else if (type == "complete") { ScanProgress.IsIndeterminate = false; ScanProgress.Value = 100; _records = item["records"]!.AsArray(); RefreshArchiveLookup(); RenderRows(_pendingOnly, false); ProgressText.Text = $"识别完成，共 {_records.Count} 张"; }
        }); }
        catch (Exception ex) { ProgressText.Text = $"识别失败：{ex.Message}"; }
        finally { ScanProgress.IsIndeterminate = false; ScanButton.IsEnabled = true; CancelButton.Visibility = Visibility.Collapsed; }
    }

    private void OnCancelScan(object sender, RoutedEventArgs e)
    {
        if (_worker is { HasExited: false }) _worker.Kill(true);
        _worker = null; StopPreviewWorker(); WarmPreviewWorker(); ScanProgress.IsIndeterminate = false; ProgressText.Text = "已取消识别"; ScanButton.IsEnabled = true; CancelButton.Visibility = Visibility.Collapsed;
    }

    private void OnReset(object sender, RoutedEventArgs e)
    {
        OnCancelScan(sender, e); StopPreviewWorker(); _records = new JsonArray(); _selected = null; _pendingOnly = false; _previewCache.Clear(); RecordRows.Children.Clear(); PreviewImage.Source = null; InputPathText.Text = "未选择"; ArchivePathText.Text = "未选择"; ScanProgress.Value = 0; TotalCountText.Text = "0"; ReviewCountText.Text = "0"; ConfirmedCountText.Text = "0"; DuplicateCountText.Text = "0"; TotalAmountSummaryText.Text = "¥0.00"; ReviewToggleButton.Content = "打开核对  0"; PendingOnlyButton.Content = "仅看待确认  0"; ReviewMetaText.Text = "请从表格中选择一张发票"; SummaryText.Text = "选择发票文件夹后开始识别"; ProgressText.Text = "已重新开始";
    }

    private static string WorkerPath => Path.Combine(AppContext.BaseDirectory, "Backend", "InvoiceToolbox.Worker.exe");

    private static Process CreateWorkerProcess()
    {
        var utf8 = new UTF8Encoding(false);
        return new Process { StartInfo = new ProcessStartInfo(WorkerPath) { WorkingDirectory = AppContext.BaseDirectory, UseShellExecute = false, RedirectStandardInput = true, RedirectStandardOutput = true, RedirectStandardError = true, StandardInputEncoding = utf8, StandardOutputEncoding = utf8, StandardErrorEncoding = utf8, CreateNoWindow = true } };
    }

    private void WarmPreviewWorker()
    {
        if (_previewWorker is { HasExited: false }) return;
        StopPreviewWorker();
        if (!File.Exists(WorkerPath)) return;
        _previewWorker = CreateWorkerProcess();
        _previewWorker.Start();
    }

    private void StopPreviewWorker()
    {
        try { if (_previewWorker is { HasExited: false }) _previewWorker.Kill(true); } catch { }
        _previewWorker?.Dispose(); _previewWorker = null;
    }

    private async Task<JsonObject> RunWarmWorkerCommandAsync(string request, string expectedEvent, Action<JsonObject>? onMessage = null)
    {
        await _previewLock.WaitAsync();
        try
        {
            WarmPreviewWorker();
            var process = _previewWorker ?? throw new InvalidOperationException("预览组件启动失败");
            await process.StandardInput.WriteLineAsync(request); await process.StandardInput.FlushAsync();
            while (true)
            {
                var line = await process.StandardOutput.ReadLineAsync();
                if (line == null) throw new OperationCanceledException("识别已取消");
                if (string.IsNullOrWhiteSpace(line)) continue;
                if (JsonNode.Parse(line) is not JsonObject message) continue;
                if (message["ok"]?.GetValue<bool>() == false) throw new InvalidOperationException(message["error"]?.GetValue<string>() ?? "预览失败");
                onMessage?.Invoke(message);
                if (message["event"]?.GetValue<string>() == "progress") await Task.Delay(16);
                if (message["event"]?.GetValue<string>() == expectedEvent) return message;
            }
        }
        finally { _previewLock.Release(); }
    }

    private async Task<string> GetPreviewAsync(string source)
    {
        var request = JsonSerializer.Serialize(new { command = "preview", path = source });
        var result = await RunWarmWorkerCommandAsync(request, "preview_complete");
        return result["path"]?.GetValue<string>() ?? "";
    }

    private async Task WarmPreviewBackendAsync()
    {
        try { await RunWarmWorkerCommandAsync(JsonSerializer.Serialize(new { command = "warmup" }), "warmup_complete"); } catch { }
    }

    private async Task RunWorkerAsync(string request, Action<JsonObject> onMessage)
    {
        if (!File.Exists(WorkerPath)) throw new FileNotFoundException("本地识别组件不存在", WorkerPath);
        using var process = CreateWorkerProcess();
        _worker = process;
        try
        {
            process.Start(); await process.StandardInput.WriteLineAsync(request); process.StandardInput.Close();
            while (!process.StandardOutput.EndOfStream)
            {
                var line = await process.StandardOutput.ReadLineAsync(); if (string.IsNullOrWhiteSpace(line)) continue;
                if (JsonNode.Parse(line) is not JsonObject item) continue;
                if (item["ok"]?.GetValue<bool>() == false)
                    throw new InvalidOperationException(item["error"]?.GetValue<string>() ?? "本地识别组件运行失败");
                onMessage(item);
                if (item["event"]?.GetValue<string>() == "progress") await Task.Delay(12);
            }
            var error = await process.StandardError.ReadToEndAsync();
            await process.WaitForExitAsync();
            if (process.ExitCode != 0) throw new InvalidOperationException(string.IsNullOrWhiteSpace(error) ? $"本地识别组件异常退出（{process.ExitCode}）" : error.Trim());
        }
        finally { if (ReferenceEquals(_worker, process)) _worker = null; }
    }

    private async void RenderRows(bool pendingOnly = false, bool allowYield = true)
    {
        var generation = ++_renderGeneration;
        RecordRows.Children.Clear(); _renderedRowGrids.Clear(); var review = 0; var shown = 0; var duplicates = 0; decimal recognizedUniqueAmountTotal = 0; var identities = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var node in _records)
        {
            var item = node!.AsObject(); var pending = item["fields_needing_review"]?.AsArray().Count > 0; if (pending) review++; var isDuplicate = !identities.Add($"{Text(item,"invoice_no")}|{Text(item,"seller_tax")}|{Text(item,"total_amount")}"); if (isDuplicate) duplicates++; if (!isDuplicate && !pending && decimal.TryParse(Text(item,"total_amount"), NumberStyles.Any, CultureInfo.InvariantCulture, out var amount)) recognizedUniqueAmountTotal += amount;
            if (pendingOnly && !pending) continue; shown++;
            var values = new[] { Text(item,"buyer_name"), Text(item,"buyer_tax"), Text(item,"seller_name"), Text(item,"seller_tax"), Text(item,"invoice_date"), Text(item,"pretax_amount"), Text(item,"tax_amount"), Text(item,"total_amount"), Text(item,"tax_rate"), Text(item,"invoice_type"), Text(item,"invoice_no"), Text(item,"category"), Text(item,"invoice_date").Length >= 7 ? Text(item,"invoice_date")[..7] : "" };
            var row = new Grid { MinWidth = _columnWidths.Sum(), ColumnSpacing = 0 };
            _renderedRowGrids.Add(row);
            for (var i = 0; i < _columnWidths.Length; i++) row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(_columnWidths[i]) });
            var dark = RootLayout.RequestedTheme == ElementTheme.Dark; var divider = new Microsoft.UI.Xaml.Media.SolidColorBrush(dark ? Windows.UI.Color.FromArgb(255, 52, 57, 66) : Windows.UI.Color.FromArgb(255, 225, 228, 234));
            var pendingBrush = new Microsoft.UI.Xaml.Media.SolidColorBrush(dark ? Windows.UI.Color.FromArgb(255, 255, 150, 170) : Windows.UI.Color.FromArgb(255, 190, 24, 72));
            for (var i = 0; i < values.Length; i++) { var cell = new TextBlock { Text = values[i], TextTrimming = TextTrimming.CharacterEllipsis, VerticalAlignment = VerticalAlignment.Center, HorizontalAlignment = HorizontalAlignment.Center, TextAlignment = TextAlignment.Center, Foreground = pending ? pendingBrush : FieldBrush(i, dark), FontWeight = pending ? Microsoft.UI.Text.FontWeights.SemiBold : Microsoft.UI.Text.FontWeights.Normal }; var frame = new Border { BorderBrush = divider, BorderThickness = new Thickness(0, 0, 1, 0), Child = cell }; Grid.SetColumn(frame, i); row.Children.Add(frame); }
            var sourcePath = Text(item,"original_path"); var archivePath = Text(item,"archived_path"); if (string.IsNullOrWhiteSpace(archivePath) && _archiveLookup.TryGetValue(Text(item,"invoice_no"), out var foundArchive)) { archivePath = foundArchive; item["archived_path"] = archivePath; }
            var sourceButton = new Button { Content = "打开源文件", Width = 94, Padding = new Thickness(6, 3, 6, 3), HorizontalAlignment = HorizontalAlignment.Center, VerticalAlignment = VerticalAlignment.Center }; sourceButton.Click += (_, _) => OpenLocalPath(sourcePath); Grid.SetColumn(sourceButton, 13); row.Children.Add(sourceButton);
            var archiveButton = new Button { Content = "打开归档", Width = 94, Padding = new Thickness(6, 3, 6, 3), HorizontalAlignment = HorizontalAlignment.Center, VerticalAlignment = VerticalAlignment.Center, IsEnabled = File.Exists(archivePath) }; archiveButton.Click += (_, _) => OpenLocalPath(archivePath); Grid.SetColumn(archiveButton, 14); row.Children.Add(archiveButton);
            var status = new TextBlock { Text = pending ? "待确认" : "已确认", HorizontalAlignment = HorizontalAlignment.Center, TextAlignment = TextAlignment.Center, VerticalAlignment = VerticalAlignment.Center, Foreground = pending ? new Microsoft.UI.Xaml.Media.SolidColorBrush(Windows.UI.Color.FromArgb(255, 213, 138, 24)) : new Microsoft.UI.Xaml.Media.SolidColorBrush(Windows.UI.Color.FromArgb(255, 36, 168, 107)) }; Grid.SetColumn(status, 15); row.Children.Add(status);
            var rowColor = pending ? (dark ? Windows.UI.Color.FromArgb(255, 67, 28, 42) : Windows.UI.Color.FromArgb(255, 255, 235, 241)) : dark ? (shown % 2 == 0 ? Windows.UI.Color.FromArgb(255, 22, 26, 32) : Windows.UI.Color.FromArgb(255, 16, 20, 26)) : (shown % 2 == 0 ? Windows.UI.Color.FromArgb(255, 248, 249, 251) : Windows.UI.Color.FromArgb(255, 255, 255, 255));
            var container = new Border { Padding = new Thickness(12, 7, 12, 7), Background = new Microsoft.UI.Xaml.Media.SolidColorBrush(rowColor), BorderBrush = divider, BorderThickness = new Thickness(0, 0, 0, 1), Child = row };
            container.Tag = container.Background; container.PointerEntered += OnInvoiceRowEnter; container.PointerExited += OnInvoiceRowExit;
            container.Tapped += async (_, e) => { if (!IsInsideButton(e.OriginalSource)) await SelectRecordAsync(item); }; RecordRows.Children.Add(container);
            if (allowYield && shown % 12 == 0)
            {
                await Task.Yield();
                if (generation != _renderGeneration) return;
            }
        }
        if (generation != _renderGeneration) return;
        TotalCountText.Text = _records.Count.ToString(); ReviewCountText.Text = review.ToString(); ConfirmedCountText.Text = (_records.Count - review).ToString(); DuplicateCountText.Text = duplicates.ToString(); TotalAmountSummaryText.Text = $"¥{recognizedUniqueAmountTotal:N2}"; ReviewToggleButton.Content = _reviewPanelVisible ? "收起核对" : $"打开核对  {review}"; PendingOnlyButton.Content = _pendingOnly ? "显示全部" : $"仅看待确认  {review}"; SummaryText.Text = pendingOnly ? $"仅显示 {shown} 张待确认发票" : $"共 {_records.Count} 张发票，{review} 张需要人工核对";
    }

    private static bool IsInsideButton(object source)
    {
        var current = source as DependencyObject;
        while (current != null) { if (current is Button) return true; current = Microsoft.UI.Xaml.Media.VisualTreeHelper.GetParent(current); }
        return false;
    }

    private static Microsoft.UI.Xaml.Media.Brush FieldBrush(int index, bool dark)
    {
        var light = new[] { "#0F766E", "#4D7C0F", "#1D4ED8", "#A16207", "#334155", "#0369A1", "#B45309", "#047857", "#B45309", "#334155", "#64748B", "#A16207", "#2563EB" };
        var deep = new[] { "#5EEAD4", "#BEF264", "#93C5FD", "#FDE047", "#BAE6FD", "#7DD3FC", "#FDE047", "#34D399", "#FACC15", "#F8FAFC", "#94A3B8", "#FBBF24", "#60A5FA" };
        var hex = (dark ? deep : light)[Math.Min(index, light.Length - 1)];
        return new Microsoft.UI.Xaml.Media.SolidColorBrush(Windows.UI.Color.FromArgb(255, Convert.ToByte(hex.Substring(1, 2), 16), Convert.ToByte(hex.Substring(3, 2), 16), Convert.ToByte(hex.Substring(5, 2), 16)));
    }

    private void OnInvoiceRowEnter(object sender, PointerRoutedEventArgs e)
    {
        if (sender is Border row) row.Background = new Microsoft.UI.Xaml.Media.SolidColorBrush(RootLayout.RequestedTheme == ElementTheme.Dark ? Windows.UI.Color.FromArgb(255, 40, 37, 45) : Windows.UI.Color.FromArgb(255, 255, 239, 246));
    }

    private static void OnInvoiceRowExit(object sender, PointerRoutedEventArgs e)
    {
        if (sender is Border { Tag: Microsoft.UI.Xaml.Media.Brush original } row) row.Background = original;
    }

    private async Task SelectRecordAsync(JsonObject item)
    {
        if (!_reviewPanelVisible) OnToggleReviewPanel(this, new RoutedEventArgs());
        _selected = item; InvoiceNoInput.Text = Text(item,"invoice_no"); BuyerTaxInput.Text = Text(item,"buyer_tax"); InvoiceDateInput.Text = Text(item,"invoice_date"); TotalAmountInput.Text = Text(item,"total_amount"); SellerNameInput.Text = Text(item,"seller_name"); SellerTaxInput.Text = Text(item,"seller_tax"); BuyerNameInput.Text = Text(item,"buyer_name"); TaxAmountInput.Text = Text(item,"tax_amount"); InvoiceTypeInput.Text = Text(item,"invoice_type"); CategoryInput.Text = Text(item,"category");
        ReviewMetaText.Text = $"发票号码：{Text(item,"invoice_no")}    开票日期：{Text(item,"invoice_date")}";
        var source = Text(item,"original_path"); var requestId = ++_previewRequestId;
        PreviewLoadingRing.Visibility = Visibility.Visible; PreviewLoadingRing.IsActive = true;
        try
        {
            if (_previewCache.TryGetValue(source, out var cached) && File.Exists(cached)) { PreviewImage.Source = new BitmapImage(new Uri(cached)); return; }
            var path = await GetPreviewAsync(source);
            if (requestId == _previewRequestId && !string.IsNullOrWhiteSpace(path) && File.Exists(path)) { _previewCache[source] = path; PreviewImage.Source = new BitmapImage(new Uri(path)); }
        }
        finally { if (requestId == _previewRequestId) { PreviewLoadingRing.IsActive = false; PreviewLoadingRing.Visibility = Visibility.Collapsed; } }
    }

    private void OnSaveReview(object sender, RoutedEventArgs e)
    {
        if (_selected == null) return; _selected["invoice_no"] = InvoiceNoInput.Text; _selected["buyer_tax"] = BuyerTaxInput.Text; _selected["invoice_date"] = InvoiceDateInput.Text; _selected["total_amount"] = TotalAmountInput.Text; _selected["seller_name"] = SellerNameInput.Text; _selected["seller_tax"] = SellerTaxInput.Text; _selected["buyer_name"] = BuyerNameInput.Text; _selected["tax_amount"] = TaxAmountInput.Text; _selected["invoice_type"] = InvoiceTypeInput.Text; _selected["category"] = string.IsNullOrWhiteSpace(CategoryInput.Text) ? "（未分类）" : CategoryInput.Text.Trim(); _selected["fields_needing_review"] = new JsonArray(); RenderRows(); ProgressText.Text = "已保存当前发票修改";
    }

    private void OnAddCategory(object sender, RoutedEventArgs e)
    {
        var value = CategoryInput.Text.Trim();
        if (string.IsNullOrWhiteSpace(value) && CategoryInput.SelectedItem is ComboBoxItem selected) value = selected.Content?.ToString()?.Trim() ?? "";
        if (string.IsNullOrWhiteSpace(value)) { CategoryFeedbackText.Text = "请先输入分类名称"; return; }
        var existing = CategoryInput.Items.OfType<ComboBoxItem>().FirstOrDefault(item => string.Equals(item.Content?.ToString(), value, StringComparison.OrdinalIgnoreCase));
        if (existing == null) { existing = new ComboBoxItem { Content = value }; CategoryInput.Items.Add(existing); }
        CategoryInput.SelectedItem = existing; CategoryInput.Text = value; SaveCategories(); CategoryFeedbackText.Text = $"已永久添加：{value}"; ProgressText.Text = $"已添加业务分类：{value}";
    }

    private void OnDeleteCategory(object sender, RoutedEventArgs e)
    {
        var value = CategoryInput.Text.Trim();
        if (string.IsNullOrWhiteSpace(value) && CategoryInput.SelectedItem is ComboBoxItem selected) value = selected.Content?.ToString()?.Trim() ?? "";
        var existing = CategoryInput.Items.OfType<ComboBoxItem>().FirstOrDefault(item => string.Equals(item.Content?.ToString(), value, StringComparison.OrdinalIgnoreCase));
        if (existing == null) { CategoryFeedbackText.Text = "该分类不在预设中"; return; }
        CategoryInput.Items.Remove(existing); CategoryInput.SelectedItem = null; CategoryInput.Text = ""; SaveCategories(); CategoryFeedbackText.Text = $"已删除：{value}";
    }

    private void LoadCategories()
    {
        var defaults = new[] { "办公用品", "技术服务", "差旅交通", "硬件设备" };
        IEnumerable<string> categories = defaults;
        try
        {
            if (ApplicationData.Current.LocalSettings.Values["BusinessCategories"] is string json)
                categories = JsonSerializer.Deserialize<string[]>(json) ?? defaults;
        }
        catch { categories = defaults; }
        CategoryInput.Items.Clear();
        foreach (var value in categories.Where(value => !string.IsNullOrWhiteSpace(value)).Distinct(StringComparer.OrdinalIgnoreCase)) CategoryInput.Items.Add(new ComboBoxItem { Content = value });
    }

    private void SaveCategories()
    {
        var categories = CategoryInput.Items.OfType<ComboBoxItem>().Select(item => item.Content?.ToString()).Where(value => !string.IsNullOrWhiteSpace(value)).ToArray();
        ApplicationData.Current.LocalSettings.Values["BusinessCategories"] = JsonSerializer.Serialize(categories);
    }

    private void OnZoomIn(object sender, RoutedEventArgs e) => SetZoom(_zoom + 0.2);
    private void OnZoomOut(object sender, RoutedEventArgs e) => SetZoom(_zoom - 0.2);
    private void OnFitPreview(object sender, RoutedEventArgs e) { SetZoom(1); PreviewTransform.TranslateX = 0; PreviewTransform.TranslateY = 0; }
    private void OnActualSize(object sender, RoutedEventArgs e) { if (PreviewImage.Source is BitmapImage image && image.PixelWidth > 0 && image.PixelHeight > 0) { var fit = Math.Min(PreviewImage.ActualWidth / image.PixelWidth, PreviewImage.ActualHeight / image.PixelHeight); SetZoom(fit > 0 ? 1 / fit : 1); } PreviewTransform.TranslateX = 0; PreviewTransform.TranslateY = 0; }
    private void SetZoom(double value) { _zoom = Math.Clamp(value, 0.25, 6); PreviewTransform.ScaleX = _zoom; PreviewTransform.ScaleY = _zoom; }
    private void OnRotateLeft(object sender, RoutedEventArgs e) => PreviewTransform.Rotation = (PreviewTransform.Rotation - 90) % 360;
    private void OnRotateRight(object sender, RoutedEventArgs e) => PreviewTransform.Rotation = (PreviewTransform.Rotation + 90) % 360;
    private void OnPreviewWheel(object sender, PointerRoutedEventArgs e) { SetZoom(_zoom + (e.GetCurrentPoint(PreviewImage).Properties.MouseWheelDelta > 0 ? 0.15 : -0.15)); e.Handled = true; }
    private void OnPreviewPressed(object sender, PointerRoutedEventArgs e) { _dragging = true; _dragStart = e.GetCurrentPoint(PreviewViewport).Position; _startX = PreviewTransform.TranslateX; _startY = PreviewTransform.TranslateY; PreviewViewport.CapturePointer(e.Pointer); e.Handled = true; }
    private void OnPreviewMoved(object sender, PointerRoutedEventArgs e) { if (!_dragging) return; var point = e.GetCurrentPoint(PreviewViewport).Position; PreviewTransform.TranslateX = _startX + point.X - _dragStart.X; PreviewTransform.TranslateY = _startY + point.Y - _dragStart.Y; e.Handled = true; }
    private void OnPreviewReleased(object sender, PointerRoutedEventArgs e) { _dragging = false; PreviewViewport.ReleasePointerCapture(e.Pointer); e.Handled = true; }

    private void OnExport(object sender, RoutedEventArgs e)
    {
        if (_records.Count == 0 || !Directory.Exists(ArchivePathText.Text)) { ProgressText.Text = "请先完成识别并选择归档文件夹"; return; }
        ExportSettingsOverlay.Visibility = Visibility.Visible;
    }

    private void OnCloseExportSettings(object sender, RoutedEventArgs e) => ExportSettingsOverlay.Visibility = Visibility.Collapsed;

    private async void OnConfirmExport(object sender, RoutedEventArgs e)
    {
        ExportSettingsOverlay.Visibility = Visibility.Collapsed;
        var mode = ArchiveModeCombo.SelectedIndex == 1 ? "category_month" : ArchiveModeCombo.SelectedIndex == 2 ? "seller_month" : "month";
        var nameFields = new JsonArray();
        foreach (var key in SelectedFieldKeys(NameFieldsList)) nameFields.Add(key);
        if (nameFields.Count == 0) nameFields.Add("invoice_no");
        var reportFields = new JsonArray();
        foreach (var key in SelectedFieldKeys(ReportFieldsList)) reportFields.Add(key);
        if (reportFields.Count == 0) reportFields.Add("invoice_no");
        var separator = string.IsNullOrWhiteSpace(NameSeparatorInput.Text) ? "_" : NameSeparatorInput.Text.Trim();
        var request = new JsonObject { ["command"] = "export", ["output_folder"] = ArchivePathText.Text, ["archive_mode"] = mode, ["name_fields"] = nameFields, ["name_separator"] = separator, ["report_fields"] = reportFields, ["records"] = _records.DeepClone() };
        ExportButton.IsEnabled = false; ProgressText.Text = "正在导出报表并归档…";
        try { var message = await RunWarmWorkerCommandAsync(request.ToJsonString(), "export_complete"); if (message["records"] is JsonArray archivedRecords) { _records = archivedRecords.DeepClone().AsArray(); RenderRows(); } ProgressText.Text = "导出与归档完成"; ExportResultTitle.Text = "导出完成"; ExportResultMessage.Text = "报表与发票已整理完毕，可以直接打开归档文件夹。"; ExportPathText.Text = ArchivePathText.Text; ExportPathPanel.Visibility = Visibility.Visible; ExportOpenButton.Visibility = Visibility.Visible; ExportResultIcon.Glyph = "\uE73E"; ExportResultIcon.Foreground = new Microsoft.UI.Xaml.Media.SolidColorBrush(Windows.UI.Color.FromArgb(255, 36, 168, 107)); ExportOverlay.Visibility = Visibility.Visible; }
        catch (Exception ex) { ProgressText.Text = $"导出失败：{ex.Message}"; ExportResultTitle.Text = "导出失败"; ExportResultMessage.Text = ex.Message; ExportPathPanel.Visibility = Visibility.Collapsed; ExportOpenButton.Visibility = Visibility.Collapsed; ExportResultIcon.Glyph = "\uE711"; ExportResultIcon.Foreground = new Microsoft.UI.Xaml.Media.SolidColorBrush(Windows.UI.Color.FromArgb(255, 210, 58, 72)); ExportOverlay.Visibility = Visibility.Visible; }
        finally { ExportButton.IsEnabled = true; }
    }

    private void OnCloseExport(object sender, RoutedEventArgs e) => ExportOverlay.Visibility = Visibility.Collapsed;
    private void OnOpenExportFolder(object sender, RoutedEventArgs e)
    {
        ExportOverlay.Visibility = Visibility.Collapsed;
        Process.Start(new ProcessStartInfo("explorer.exe", $"\"{ArchivePathText.Text}\"") { UseShellExecute = true });
    }

    private static void OpenLocalPath(string path)
    {
        if (File.Exists(path)) Process.Start(new ProcessStartInfo(path) { UseShellExecute = true });
    }

    private static string Text(JsonObject item, string name) => item[name]?.GetValue<string>() ?? "";
}
