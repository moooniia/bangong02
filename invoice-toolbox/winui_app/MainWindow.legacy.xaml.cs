using Microsoft.UI;
using Microsoft.UI.Windowing;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Media;
using Microsoft.UI.Xaml.Media.Imaging;
using Microsoft.UI.Xaml.Input;
using System;
using System.Collections.ObjectModel;
using System.Diagnostics;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using System.Text.Json.Nodes;
using Windows.Storage.Pickers;
using WinRT.Interop;

namespace InvoiceToolbox.WinUI;

public sealed class MainWindow : Window
{
    private readonly Grid _root;
    private readonly StackPanel _reviewPanel;
    private readonly TextBlock _inputPathText;
    private readonly TextBlock _archivePathText;
    private readonly TextBlock _statusText;
    private readonly Grid _reviewRegion;
    private readonly StackPanel _recordStack;
    private readonly TextBlock _centerStatus;
    private readonly TextBlock _reviewText;
    private readonly Image _previewImage;
    private readonly StackPanel _reviewFieldsPanel;
    private readonly Dictionary<string, TextBox> _reviewInputs = new();
    private int _selectedRowId;
    private readonly Button _cancelButton;
    private readonly Border _progressFill;
    private readonly Grid _titleBar;
    private readonly Grid _body;
    private double _previewScale = 1;
    private double _previewRotation;
    private readonly CompositeTransform _previewTransform = new();
    private bool _draggingPreview;
    private Windows.Foundation.Point _previewDragStart;
    private double _previewStartX;
    private double _previewStartY;
    private Process? _worker;
    private string _recordsJson = "[]";
    private bool _darkMode;

    public MainWindow()
    {
        _root = new Grid { Background = new SolidColorBrush(ColorHelper.FromArgb(255, 248, 248, 250)) };
        _reviewPanel = new StackPanel();
        _reviewRegion = new Grid { Background = new SolidColorBrush(Colors.White), Visibility = Visibility.Collapsed };
        _root.RowDefinitions.Add(new RowDefinition { Height = new GridLength(52) });
        _root.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
        _titleBar = new Grid { Background = new SolidColorBrush(Colors.White) };
        var logo = new Border { Width = 30, Height = 30, CornerRadius = new CornerRadius(9), Background = new SolidColorBrush(ColorHelper.FromArgb(255, 239, 72, 139)), Margin = new Thickness(18, 0, 0, 0) };
        logo.Child = new FontIcon { Glyph = "\uE8A1", FontSize = 16, Foreground = new SolidColorBrush(Colors.White) };
        _titleBar.Children.Add(logo);
        _titleBar.Children.Add(new TextBlock { Text = "\u53d1\u7968\u5de5\u5177\u7bb1   \u6279\u91cf\u8bc6\u522b \u00b7 \u5f52\u6863 \u00b7 \u6838\u5bf9", FontSize = 16, FontWeight = Microsoft.UI.Text.FontWeights.SemiBold, VerticalAlignment = VerticalAlignment.Center, Margin = new Thickness(60, 0, 0, 0) });
        var toolbar = new StackPanel { Orientation = Orientation.Horizontal, Spacing = 6, HorizontalAlignment = HorizontalAlignment.Right, Margin = new Thickness(0, 8, 18, 8) };
        var themeToggle = new Button { Content = "\u6d45 / \u6df1" };
        themeToggle.Click += (_, _) => ToggleTheme();
        toolbar.Children.Add(themeToggle);
        var reviewToggle = new Button { Content = "\u4eba\u5de5\u6838\u5bf9" };
        reviewToggle.Click += (_, _) => _reviewRegion.Visibility = _reviewRegion.Visibility == Visibility.Visible ? Visibility.Collapsed : Visibility.Visible;
        toolbar.Children.Add(reviewToggle);
        _titleBar.Children.Add(toolbar);
        Grid.SetRow(_titleBar, 0);
        _root.Children.Add(_titleBar);
        _body = new Grid { Background = new SolidColorBrush(ColorHelper.FromArgb(255, 248, 248, 250)) };
        _body.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(292) });
        _body.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        _body.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(360) });
        var sidebar = new StackPanel { Spacing = 10, Margin = new Thickness(20) };
        sidebar.Children.Add(new TextBlock { Text = "\u53d1\u7968\u5de5\u5177\u7bb1", FontSize = 20, FontWeight = Microsoft.UI.Text.FontWeights.SemiBold });
        sidebar.Children.Add(new TextBlock { Text = "\u53d1\u7968\u6587\u4ef6\u5939", Margin = new Thickness(0, 14, 0, 0) });
        _inputPathText = new TextBlock { Text = "\u672a\u9009\u62e9", Opacity = 0.62, TextTrimming = TextTrimming.CharacterEllipsis };
        sidebar.Children.Add(_inputPathText);
        var chooseInput = new Button { Content = "\u9009\u62e9\u6587\u4ef6\u5939" };
        chooseInput.Click += async (_, _) => await PickFolderAsync(_inputPathText);
        sidebar.Children.Add(chooseInput);
        sidebar.Children.Add(new TextBlock { Text = "\u5f52\u6863\u6587\u4ef6\u5939", Margin = new Thickness(0, 8, 0, 0) });
        _archivePathText = new TextBlock { Text = "\u672a\u9009\u62e9", Opacity = 0.62, TextTrimming = TextTrimming.CharacterEllipsis };
        sidebar.Children.Add(_archivePathText);
        var chooseArchive = new Button { Content = "\u9009\u62e9\u6587\u4ef6\u5939" };
        chooseArchive.Click += async (_, _) => await PickFolderAsync(_archivePathText);
        sidebar.Children.Add(chooseArchive);
        sidebar.Children.Add(new TextBlock { Text = "\u5f52\u6863\u89c4\u5219", Margin = new Thickness(0, 10, 0, 0) });
        sidebar.Children.Add(new RadioButton { Content = "\u6309\u5f00\u7968\u5e74\u6708", IsChecked = true });
        sidebar.Children.Add(new RadioButton { Content = "\u6309\u4e1a\u52a1\u5206\u7c7b / \u5e74\u6708" });
        sidebar.Children.Add(new RadioButton { Content = "\u6309\u9500\u552e\u65b9 / \u5e74\u6708" });
        _statusText = new TextBlock { Text = "\u5c31\u7eea", Opacity = 0.68, Margin = new Thickness(0, 14, 0, 0) };
        sidebar.Children.Add(_statusText);
        var progressTrack = new Border { Height = 8, Background = new SolidColorBrush(ColorHelper.FromArgb(255, 232, 232, 236)), CornerRadius = new CornerRadius(4), HorizontalAlignment = HorizontalAlignment.Stretch };
        _progressFill = new Border { Width = 0, HorizontalAlignment = HorizontalAlignment.Left, Background = new SolidColorBrush(ColorHelper.FromArgb(255, 233, 68, 135)), CornerRadius = new CornerRadius(4) };
        progressTrack.Child = _progressFill;
        sidebar.Children.Add(progressTrack);
        var scan = new Button { Content = "\u5f00\u59cb\u8bc6\u522b" };
        scan.Click += (_, _) => StartScan();
        sidebar.Children.Add(scan);
        _cancelButton = new Button { Content = "\u53d6\u6d88\u8bc6\u522b", Visibility = Visibility.Collapsed };
        _cancelButton.Click += (_, _) => CancelScan();
        sidebar.Children.Add(_cancelButton);
        var export = new Button { Content = "\u5bfc\u51fa\u62a5\u8868\u4e0e\u5f52\u6863" };
        export.Click += async (_, _) => await ExportAsync();
        sidebar.Children.Add(export);
        var reset = new Button { Content = "\u91cd\u65b0\u5f00\u59cb" };
        reset.Click += (_, _) => ResetSession();
        sidebar.Children.Add(reset);
        var sidebarCard = new Border { Background = new SolidColorBrush(Colors.White), CornerRadius = new CornerRadius(12), Padding = new Thickness(4), Child = sidebar };
        Grid.SetColumn(sidebarCard, 0);
        _body.Children.Add(sidebarCard);
        var centerStack = new StackPanel { Spacing = 10, Margin = new Thickness(20) };
        centerStack.Children.Add(new TextBlock { Text = "\u53d1\u7968\u660e\u7ec6", FontSize = 22, FontWeight = Microsoft.UI.Text.FontWeights.SemiBold });
        _centerStatus = new TextBlock { Text = "\u8bf7\u9009\u62e9\u53d1\u7968\u6587\u4ef6\u5939\u540e\u5f00\u59cb\u8bc6\u522b", Opacity = 0.68 };
        centerStack.Children.Add(_centerStatus);
        _recordStack = new StackPanel { Spacing = 2 };
        centerStack.Children.Add(new Border { Background = new SolidColorBrush(ColorHelper.FromArgb(255, 32, 33, 36)), Padding = new Thickness(10, 8, 10, 8), Child = new TextBlock { Text = "\u6587\u4ef6\u540d                         \u9500\u552e\u65b9                         \u4ef7\u7a0e\u5408\u8ba1                         \u72b6\u6001", Foreground = new SolidColorBrush(Colors.White) } });
        centerStack.Children.Add(_recordStack);
        var center = new ScrollViewer { Content = centerStack, HorizontalScrollBarVisibility = ScrollBarVisibility.Disabled, VerticalScrollBarVisibility = ScrollBarVisibility.Auto };
        var centerCard = new Border { Background = new SolidColorBrush(Colors.White), CornerRadius = new CornerRadius(12), Padding = new Thickness(12), Child = center };
        Grid.SetColumn(centerCard, 1);
        _body.Children.Add(centerCard);
        var reviewStack = new StackPanel { Spacing = 10, Margin = new Thickness(20) };
        reviewStack.Children.Add(new TextBlock { Text = "\u4eba\u5de5\u6838\u5bf9", FontSize = 22, FontWeight = Microsoft.UI.Text.FontWeights.SemiBold });
        _reviewText = new TextBlock { Text = "\u9009\u62e9\u4e00\u5f20\u53d1\u7968", TextWrapping = TextWrapping.Wrap, Opacity = 0.68 };
        reviewStack.Children.Add(_reviewText);
        _reviewFieldsPanel = new StackPanel { Spacing = 6 };
        reviewStack.Children.Add(_reviewFieldsPanel);
        var previewToolbar = new StackPanel { Orientation = Orientation.Horizontal, Spacing = 6 };
        var zoomOut = new Button { Content = "-" };
        zoomOut.Click += (_, _) => SetPreviewScale(_previewScale - 0.15);
        var zoomIn = new Button { Content = "+" };
        zoomIn.Click += (_, _) => SetPreviewScale(_previewScale + 0.15);
        var fit = new Button { Content = "\u9002\u5e94" };
        fit.Click += (_, _) => SetPreviewScale(1);
        var rotate = new Button { Content = "\u65cb\u8f6c" };
        rotate.Click += (_, _) => { _previewRotation = (_previewRotation + 90) % 360; _previewTransform.Rotation = _previewRotation; };
        var resetView = new Button { Content = "\u91cd\u7f6e" };
        resetView.Click += (_, _) => ResetPreviewView();
        previewToolbar.Children.Add(zoomOut);
        previewToolbar.Children.Add(zoomIn);
        previewToolbar.Children.Add(fit);
        previewToolbar.Children.Add(rotate);
        previewToolbar.Children.Add(resetView);
        reviewStack.Children.Add(previewToolbar);
        var previewScroll = new ScrollViewer { HorizontalScrollBarVisibility = ScrollBarVisibility.Auto, VerticalScrollBarVisibility = ScrollBarVisibility.Auto, Height = 390, Background = new SolidColorBrush(ColorHelper.FromArgb(255, 30, 31, 34)) };
        _previewImage = new Image { Stretch = Stretch.Uniform, HorizontalAlignment = HorizontalAlignment.Center, VerticalAlignment = VerticalAlignment.Center };
        _previewImage.RenderTransform = _previewTransform;
        _previewImage.RenderTransformOrigin = new Windows.Foundation.Point(0.5, 0.5);
        _previewImage.PointerPressed += PreviewPointerPressed;
        _previewImage.PointerMoved += PreviewPointerMoved;
        _previewImage.PointerReleased += PreviewPointerReleased;
        _previewImage.PointerCanceled += PreviewPointerReleased;
        previewScroll.Content = _previewImage;
        reviewStack.Children.Add(previewScroll);
        var saveReview = new Button { Content = "\u4fdd\u5b58\u4fee\u6539" };
        saveReview.Click += (_, _) => SaveReview();
        reviewStack.Children.Add(saveReview);
        _reviewRegion.Children.Add(reviewStack);
        var review = _reviewRegion;
        Grid.SetColumn(review, 2);
        _body.Children.Add(review);
        Grid.SetRow(_body, 1);
        _root.Children.Add(_body);
        Content = _root;
    }

    private async System.Threading.Tasks.Task PickFolderAsync(TextBlock target)
    {
        var picker = new FolderPicker();
        picker.SuggestedStartLocation = Windows.Storage.Pickers.PickerLocationId.Desktop;
        picker.FileTypeFilter.Add("*");
        InitializeWithWindow.Initialize(picker, WindowNative.GetWindowHandle(this));
        var folder = await picker.PickSingleFolderAsync();
        if (folder != null)
        {
            target.Text = folder.Path;
            target.Opacity = 1;
        }
    }

    private async void StartScan()
    {
        if (_inputPathText.Text == "\u672a\u9009\u62e9")
        {
            SetStatus("\u8bf7\u5148\u9009\u62e9\u53d1\u7968\u6587\u4ef6\u5939");
            return;
        }
        _cancelButton.Visibility = Visibility.Visible;
        _progressFill.Width = 4;
        var root = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "..", "..", ".."));
        var python = Path.Combine(root, ".venv-win", "Scripts", "python.exe");
        var worker = Path.Combine(root, "native_worker.py");
        if (!File.Exists(python) || !File.Exists(worker))
        {
            SetStatus("\u8fd0\u884c\u73af\u5883\u672a\u627e\u5230");
            return;
        }
        _worker?.Kill(entireProcessTree: true);
        _worker = new Process
        {
            StartInfo = new ProcessStartInfo
            {
                FileName = python,
                Arguments = $"\"{worker}\"",
                WorkingDirectory = root,
                UseShellExecute = false,
                RedirectStandardInput = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true,
            },
            EnableRaisingEvents = true,
        };
        _worker.Start();
        await _worker.StandardInput.WriteLineAsync(JsonSerializer.Serialize(new { command = "scan", folder = _inputPathText.Text }));
        _worker.StandardInput.Close();
        while (!_worker.StandardOutput.EndOfStream)
        {
            var line = await _worker.StandardOutput.ReadLineAsync();
            if (string.IsNullOrWhiteSpace(line)) continue;
            using var json = JsonDocument.Parse(line);
            var item = json.RootElement;
            if (item.TryGetProperty("event", out var eventValue) && eventValue.GetString() == "progress")
            {
                var done = item.GetProperty("done").GetInt32();
                var total = item.GetProperty("total").GetInt32();
                SetStatus($"\u6b63\u5728\u8bc6\u522b {done} / {total}");
                _centerStatus.Text = $"\u6b63\u5728\u8bc6\u522b {done} / {total}";
                _progressFill.Width = Math.Max(4, 220.0 * done / Math.Max(1, total));
            }
            else if (item.TryGetProperty("event", out eventValue) && eventValue.GetString() == "complete")
            {
                var records = item.GetProperty("records");
                _recordsJson = records.GetRawText();
                _recordStack.Children.Clear();
                foreach (var record in records.EnumerateArray())
                {
                    var reviewCount = record.GetProperty("fields_needing_review").GetArrayLength();
                    var rowGrid = new Grid { MinHeight = 34 };
                    rowGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(2, GridUnitType.Star) });
                    rowGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(2, GridUnitType.Star) });
                    rowGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
                    rowGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
                    AddCell(rowGrid, GetText(record, "original_name"), 0);
                    AddCell(rowGrid, GetText(record, "seller_name"), 1);
                    AddCell(rowGrid, GetText(record, "total_amount"), 2);
                    AddCell(rowGrid, reviewCount == 0 ? "\u5df2\u786e\u8ba4" : "\u5f85\u786e\u8ba4", 3);
                    var rowButton = new Button { Content = rowGrid, HorizontalContentAlignment = HorizontalAlignment.Stretch, HorizontalAlignment = HorizontalAlignment.Stretch, Padding = new Thickness(6, 3, 6, 3) };
                    rowButton.Background = new SolidColorBrush(reviewCount == 0 ? ColorHelper.FromArgb(255, 242, 249, 245) : ColorHelper.FromArgb(255, 255, 244, 209));
                    rowButton.Foreground = new SolidColorBrush(reviewCount == 0 ? ColorHelper.FromArgb(255, 35, 91, 61) : ColorHelper.FromArgb(255, 154, 80, 0));
                    var originalPath = GetText(record, "original_path");
                    var recordCopy = record.Clone();
                    rowButton.Click += (_, _) => ShowRecord(recordCopy, originalPath);
                    _recordStack.Children.Add(rowButton);
                }
                SetStatus($"\u8bc6\u522b\u5b8c\u6210\uff0c\u5171 {records.GetArrayLength()} \u5f20");
                _centerStatus.Text = $"\u8bc6\u522b\u5b8c\u6210\uff0c\u5171 {records.GetArrayLength()} \u5f20";
                _progressFill.Width = 220;
            }
            else if (item.TryGetProperty("error", out var error))
            {
                SetStatus(error.GetString() ?? "\u8bc6\u522b\u5931\u8d25");
            }
        }
        _worker.Dispose();
        _worker = null;
        _cancelButton.Visibility = Visibility.Collapsed;
    }

    private void CancelScan()
    {
        if (_worker != null && !_worker.HasExited)
        {
            _worker.Kill(entireProcessTree: true);
            _worker = null;
            SetStatus("\u5df2\u53d6\u6d88\u8bc6\u522b");
        }
        _cancelButton.Visibility = Visibility.Collapsed;
    }

    private void ResetSession()
    {
        _recordsJson = "[]";
        _recordStack.Children.Clear();
        _progressFill.Width = 0;
        CancelScan();
        _inputPathText.Text = "\u672a\u9009\u62e9";
        _archivePathText.Text = "\u672a\u9009\u62e9";
        _inputPathText.Opacity = 0.62;
        _archivePathText.Opacity = 0.62;
        SetStatus("\u5df2\u91cd\u7f6e\uff0c\u53ef\u5f00\u59cb\u65b0\u4efb\u52a1");
    }

    private void SetStatus(string text) => _statusText.Text = text;

    private async void ShowRecord(JsonElement record, string originalPath)
    {
        _selectedRowId = record.GetProperty("row_id").GetInt32();
        _reviewFieldsPanel.Children.Clear();
        _reviewInputs.Clear();
        foreach (var field in new[] { ("buyer_name", "\u8d2d\u4e70\u65b9"), ("buyer_tax", "\u8d2d\u4e70\u65b9\u7a0e\u53f7"), ("seller_name", "\u9500\u552e\u65b9"), ("seller_tax", "\u9500\u552e\u65b9\u7a0e\u53f7"), ("invoice_date", "\u5f00\u7968\u65e5\u671f"), ("total_amount", "\u4ef7\u7a0e\u5408\u8ba1") })
        {
            _reviewFieldsPanel.Children.Add(new TextBlock { Text = field.Item2, Opacity = 0.68 });
            var input = new TextBox { Text = GetText(record, field.Item1) };
            _reviewFieldsPanel.Children.Add(input);
            _reviewInputs[field.Item1] = input;
        }
        var reviewFields = GetText(record, "fields_needing_review");
        _reviewText.Text = $"{GetText(record, "original_name")}\n\n\u8d2d\u4e70\u65b9\uff1a{GetText(record, "buyer_name")}\n\u9500\u552e\u65b9\uff1a{GetText(record, "seller_name")}\n\u5f00\u7968\u65e5\u671f\uff1a{GetText(record, "invoice_date")}\n\u4ef7\u7a0e\u5408\u8ba1\uff1a{GetText(record, "total_amount")}\n\n\u5f85\u786e\u8ba4\u5b57\u6bb5\uff1a{reviewFields}";
        _reviewRegion.Visibility = Visibility.Visible;
        await RenderPreviewAsync(originalPath);
    }

    private void SaveReview()
    {
        if (_selectedRowId == 0) return;
        var root = JsonNode.Parse(_recordsJson)?.AsArray();
        if (root == null) return;
        foreach (var node in root)
        {
            if (node?["row_id"]?.GetValue<int>() != _selectedRowId) continue;
            foreach (var pair in _reviewInputs) node[pair.Key] = pair.Value.Text;
            _recordsJson = root.ToJsonString();
            SetStatus("\u5df2\u4fdd\u5b58\u5f53\u524d\u53d1\u7968\u4fee\u6539");
            return;
        }
    }

    private void SetPreviewScale(double scale)
    {
        _previewScale = Math.Clamp(scale, 0.4, 3.5);
        _previewTransform.ScaleX = _previewScale;
        _previewTransform.ScaleY = _previewScale;
        _previewImage.Width = 620 * _previewScale;
        _previewImage.Height = 420 * _previewScale;
    }

    private void ResetPreviewView()
    {
        _previewScale = 1;
        _previewRotation = 0;
        _previewTransform.ScaleX = 1;
        _previewTransform.ScaleY = 1;
        _previewTransform.Rotation = 0;
        _previewTransform.TranslateX = 0;
        _previewTransform.TranslateY = 0;
        _previewImage.Width = 620;
        _previewImage.Height = 420;
    }

    private void PreviewPointerPressed(object sender, PointerRoutedEventArgs args)
    {
        _draggingPreview = true;
        _previewDragStart = args.GetCurrentPoint(_previewImage).Position;
        _previewStartX = _previewTransform.TranslateX;
        _previewStartY = _previewTransform.TranslateY;
        _previewImage.CapturePointer(args.Pointer);
    }

    private void PreviewPointerMoved(object sender, PointerRoutedEventArgs args)
    {
        if (!_draggingPreview) return;
        var point = args.GetCurrentPoint(_previewImage).Position;
        _previewTransform.TranslateX = _previewStartX + point.X - _previewDragStart.X;
        _previewTransform.TranslateY = _previewStartY + point.Y - _previewDragStart.Y;
    }

    private void PreviewPointerReleased(object sender, PointerRoutedEventArgs args)
    {
        _draggingPreview = false;
        _previewImage.ReleasePointerCapture(args.Pointer);
    }

    private async System.Threading.Tasks.Task RenderPreviewAsync(string originalPath)
    {
        if (!File.Exists(originalPath)) return;
        var root = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "..", "..", ".."));
        var python = Path.Combine(root, ".venv-win", "Scripts", "python.exe");
        var workerPath = Path.Combine(root, "native_worker.py");
        if (!File.Exists(python) || !File.Exists(workerPath)) return;
        using var process = new Process
        {
            StartInfo = new ProcessStartInfo
            {
                FileName = python,
                Arguments = $"\"{workerPath}\"",
                WorkingDirectory = root,
                UseShellExecute = false,
                RedirectStandardInput = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true,
            }
        };
        process.Start();
        await process.StandardInput.WriteLineAsync(JsonSerializer.Serialize(new { command = "preview", path = originalPath }));
        process.StandardInput.Close();
        var line = await process.StandardOutput.ReadLineAsync();
        if (string.IsNullOrWhiteSpace(line)) return;
        using var json = JsonDocument.Parse(line);
        if (!json.RootElement.TryGetProperty("path", out var path)) return;
        var previewPath = path.GetString();
        if (string.IsNullOrWhiteSpace(previewPath) || !File.Exists(previewPath)) return;
        _previewImage.Source = new BitmapImage(new Uri(previewPath));
        ResetPreviewView();
    }

    private async System.Threading.Tasks.Task ExportAsync()
    {
        if (_recordsJson == "[]")
        {
            SetStatus("\u8bf7\u5148\u5b8c\u6210\u8bc6\u522b");
            return;
        }
        var output = _archivePathText.Text;
        if (output == "\u672a\u9009\u62e9")
        {
            SetStatus("\u8bf7\u5148\u9009\u62e9\u5f52\u6863\u6587\u4ef6\u5939");
            return;
        }
        var root = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "..", "..", ".."));
        var python = Path.Combine(root, ".venv-win", "Scripts", "python.exe");
        var workerPath = Path.Combine(root, "native_worker.py");
        if (!File.Exists(python) || !File.Exists(workerPath))
        {
            SetStatus("\u8fd0\u884c\u73af\u5883\u672a\u627e\u5230");
            return;
        }
        using var process = new Process
        {
            StartInfo = new ProcessStartInfo
            {
                FileName = python,
                Arguments = $"\"{workerPath}\"",
                WorkingDirectory = root,
                UseShellExecute = false,
                RedirectStandardInput = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true,
            }
        };
        process.Start();
        var command = JsonSerializer.Serialize(new { command = "export", output_folder = output, archive_mode = "month", records = JsonSerializer.Deserialize<JsonElement[]>(_recordsJson) });
        await process.StandardInput.WriteLineAsync(command);
        process.StandardInput.Close();
        var line = await process.StandardOutput.ReadLineAsync();
        if (!string.IsNullOrWhiteSpace(line))
        {
            using var json = JsonDocument.Parse(line);
            SetStatus(json.RootElement.TryGetProperty("path", out var path) ? $"\u5df2\u5b8c\u6210\uff1a{path.GetString()}" : "\u5bfc\u51fa\u5931\u8d25");
        }
    }

    private static string GetText(JsonElement item, string name)
        => item.TryGetProperty(name, out var value) ? value.GetString() ?? "" : "";

    private static void AddCell(Grid grid, string text, int column)
    {
        var cell = new TextBlock { Text = text, TextTrimming = TextTrimming.CharacterEllipsis, VerticalAlignment = VerticalAlignment.Center, Margin = new Thickness(4, 0, 10, 0) };
        Grid.SetColumn(cell, column);
        grid.Children.Add(cell);
    }

    /*
    public MainWindow()
    {
        _root = new Grid { Background = new SolidColorBrush(ColorHelper.FromArgb(255, 248, 248, 250)) };
        _reviewPanel = new StackPanel { Visibility = Visibility.Collapsed };
        _root.RowDefinitions.Add(new RowDefinition { Height = new GridLength(52) });
        _root.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });

        var title = new Border { Background = new SolidColorBrush(Colors.White), Padding = new Thickness(18, 0, 18, 0) };
        title.Child = new TextBlock { Text = "▣  发票工具箱    批量识别 · 归档 · 核对", FontSize = 16, VerticalAlignment = VerticalAlignment.Center };
        Grid.SetRow(title, 0);
        _root.Children.Add(title);

        var body = new Grid { Padding = new Thickness(16), ColumnSpacing = 16 };
        body.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(292) });
        body.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        body.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(0) });
        var sidebar = new Border { Background = new SolidColorBrush(Colors.White), CornerRadius = new CornerRadius(10), Padding = new Thickness(16) };
        var sidebarStack = new StackPanel { Spacing = 10 };
        sidebarStack.Children.Add(new TextBlock { Text = "发票工具箱", FontSize = 20, FontWeight = Microsoft.UI.Text.FontWeights.SemiBold });
        sidebarStack.Children.Add(new TextBlock { Text = "发票文件夹", Margin = new Thickness(0, 14, 0, 0) });
        sidebarStack.Children.Add(new Button { Content = "选择文件夹" });
        sidebarStack.Children.Add(new TextBlock { Text = "归档文件夹", Margin = new Thickness(0, 8, 0, 0) });
        sidebarStack.Children.Add(new Button { Content = "选择文件夹" });
        sidebarStack.Children.Add(new TextBlock { Text = "归档规则", Margin = new Thickness(0, 10, 0, 0) });
        sidebarStack.Children.Add(new RadioButton { Content = "按开票年月", IsChecked = true });
        sidebarStack.Children.Add(new RadioButton { Content = "按业务分类 / 年月" });
        sidebarStack.Children.Add(new RadioButton { Content = "按销售方 / 年月" });
        sidebarStack.Children.Add(new ProgressBar { Value = 0, Margin = new Thickness(0, 12, 0, 0) });
        var scan = new Button { Content = "开始识别" };
        scan.Background = new SolidColorBrush(ColorHelper.FromArgb(255, 233, 68, 135));
        scan.Foreground = new SolidColorBrush(Colors.White);
        sidebarStack.Children.Add(scan);
        sidebarStack.Children.Add(new Button { Content = "导出报表与归档" });
        sidebarStack.Children.Add(new Button { Content = "重新开始" });
        sidebar.Child = sidebarStack;
        body.Children.Add(sidebar);

        var center = new Border { Background = new SolidColorBrush(Colors.White), CornerRadius = new CornerRadius(10), Padding = new Thickness(20) };
        center.Child = new StackPanel
        {
            Spacing = 14,
            Children = { new TextBlock { Text = "发票明细", FontSize = 24, FontWeight = Microsoft.UI.Text.FontWeights.SemiBold }, new TextBlock { Text = "选择发票文件夹后开始识别", Opacity = 0.62 } },
        };
        Grid.SetColumn(center, 1);
        body.Children.Add(center);
        Grid.SetRow(body, 1);
        _root.Children.Add(body);
        Content = _root;
    }
    */

    private Grid BuildRoot(out StackPanel reviewPanel)
    {
        var root = new Grid { Background = new SolidColorBrush(ColorHelper.FromArgb(255, 248, 248, 250)) };
        root.RowDefinitions.Add(new RowDefinition { Height = new GridLength(52) });
        root.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });

        var titleBar = new Grid { Background = new SolidColorBrush(Colors.White), Padding = new Thickness(16, 0, 8, 0) };
        titleBar.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        titleBar.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        titleBar.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        titleBar.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        var logo = new Border { Width = 30, Height = 30, CornerRadius = new CornerRadius(8), Background = new SolidColorBrush(ColorHelper.FromArgb(255, 233, 68, 135)) };
        logo.Child = new FontIcon { Glyph = "\uE8A1", Foreground = new SolidColorBrush(Colors.White), FontSize = 17 };
        titleBar.Children.Add(logo);
        var brand = new StackPanel { Margin = new Thickness(10, 0, 0, 0), VerticalAlignment = VerticalAlignment.Center };
        brand.Children.Add(new TextBlock { Text = "发票工具箱", FontSize = 16, FontWeight = Microsoft.UI.Text.FontWeights.SemiBold });
        brand.Children.Add(new TextBlock { Text = "批量识别 · 归档 · 核对", FontSize = 10, Opacity = 0.62 });
        Grid.SetColumn(brand, 1);
        titleBar.Children.Add(brand);
        var toolbar = new StackPanel { Orientation = Orientation.Horizontal, Spacing = 6 };
        var theme = new Button { Content = new FontIcon { Glyph = "\uE706" }, Width = 40, Height = 36 };
        theme.Click += (_, _) => ToggleTheme();
        var about = new Button { Content = new FontIcon { Glyph = "\uE946" }, Width = 40, Height = 36 };
        about.Click += (_, _) => ShowAbout();
        toolbar.Children.Add(theme);
        toolbar.Children.Add(about);
        Grid.SetColumn(toolbar, 3);
        titleBar.Children.Add(toolbar);
        Grid.SetRow(titleBar, 0);
        root.Children.Add(titleBar);

        var body = new Grid { Padding = new Thickness(16, 12, 16, 16), ColumnSpacing = 16 };
        body.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(292) });
        body.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        body.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(420) });
        Grid.SetRow(body, 1);
        root.Children.Add(body);
        body.Children.Add(BuildSidebar());
        var center = BuildCenter();
        Grid.SetColumn(center, 1);
        body.Children.Add(center);
        reviewPanel = BuildReviewPanel();
        Grid.SetColumn(reviewPanel, 2);
        body.Children.Add(reviewPanel);
        return root;
    }

    private FrameworkElement BuildSidebar()
    {
        var panel = new Border { Background = new SolidColorBrush(Colors.White), CornerRadius = new CornerRadius(10), Padding = new Thickness(16) };
        var stack = new StackPanel { Spacing = 12 };
        stack.Children.Add(new TextBlock { Text = "发票工具箱", FontSize = 20, FontWeight = Microsoft.UI.Text.FontWeights.SemiBold });
        stack.Children.Add(new TextBlock { Text = "发票文件夹", FontSize = 14, FontWeight = Microsoft.UI.Text.FontWeights.SemiBold, Margin = new Thickness(0, 10, 0, 0) });
        stack.Children.Add(new Button { Content = "选择文件夹", HorizontalAlignment = HorizontalAlignment.Left });
        stack.Children.Add(new TextBlock { Text = "归档文件夹", FontSize = 14, FontWeight = Microsoft.UI.Text.FontWeights.SemiBold, Margin = new Thickness(0, 6, 0, 0) });
        stack.Children.Add(new Button { Content = "选择文件夹", HorizontalAlignment = HorizontalAlignment.Left });
        stack.Children.Add(new TextBlock { Text = "归档规则", FontSize = 14, FontWeight = Microsoft.UI.Text.FontWeights.SemiBold, Margin = new Thickness(0, 10, 0, 0) });
        stack.Children.Add(new RadioButton { Content = "按开票年月", IsChecked = true });
        stack.Children.Add(new RadioButton { Content = "按业务分类 / 年月" });
        stack.Children.Add(new RadioButton { Content = "按销售方 / 年月" });
        stack.Children.Add(new ProgressBar { Minimum = 0, Maximum = 100, Value = 0, Margin = new Thickness(0, 10, 0, 0) });
        var scan = new Button { Content = "开始识别", HorizontalAlignment = HorizontalAlignment.Stretch };
        scan.Background = new SolidColorBrush(ColorHelper.FromArgb(255, 233, 68, 135));
        scan.Foreground = new SolidColorBrush(Colors.White);
        stack.Children.Add(scan);
        stack.Children.Add(new Button { Content = "导出报表与归档" });
        stack.Children.Add(new Button { Content = "重新开始" });
        panel.Child = stack;
        return panel;
    }

    private FrameworkElement BuildCenter()
    {
        var stack = new StackPanel { Spacing = 12 };
        stack.Children.Add(new TextBlock { Text = "发票明细", FontSize = 22, FontWeight = Microsoft.UI.Text.FontWeights.SemiBold });
        var list = new ListView { SelectionMode = ListViewSelectionMode.Single };
        list.Header = new Border { Background = new SolidColorBrush(ColorHelper.FromArgb(255, 32, 33, 36)), Padding = new Thickness(14), Child = new TextBlock { Text = "公司抬头        购买方税号        销售方        开票日期        价税合计        状态", Foreground = new SolidColorBrush(Colors.White) } };
        var card = new Border { Background = new SolidColorBrush(Colors.White), CornerRadius = new CornerRadius(10), Child = list };
        stack.Children.Add(card);
        return stack;
    }

    private StackPanel BuildReviewPanel()
    {
        var stack = new StackPanel { Spacing = 10, Visibility = Visibility.Collapsed };
        stack.Children.Add(new TextBlock { Text = "人工核对", FontSize = 22, FontWeight = Microsoft.UI.Text.FontWeights.SemiBold });
        stack.Children.Add(new Border { Height = 280, Background = new SolidColorBrush(ColorHelper.FromArgb(255, 22, 23, 25)), CornerRadius = new CornerRadius(8), Child = new TextBlock { Text = "发票预览", Foreground = new SolidColorBrush(Colors.Gray), HorizontalAlignment = HorizontalAlignment.Center, VerticalAlignment = VerticalAlignment.Center } });
        foreach (var label in new[] { "购买方抬头", "购买方税号", "销售方名称", "销售方税号" })
        {
            stack.Children.Add(new TextBlock { Text = label, Opacity = 0.62 });
            stack.Children.Add(new TextBox { PlaceholderText = "待确认" });
        }
        stack.Children.Add(new Button { Content = "保存修改" });
        return stack;
    }

    private void ToggleTheme()
    {
        _darkMode = !_darkMode;
        _root.RequestedTheme = _darkMode ? ElementTheme.Dark : ElementTheme.Light;
        var surface = _darkMode ? ColorHelper.FromArgb(255, 30, 31, 34) : Colors.White;
        var canvas = _darkMode ? ColorHelper.FromArgb(255, 22, 23, 26) : ColorHelper.FromArgb(255, 248, 248, 250);
        _titleBar.Background = new SolidColorBrush(surface);
        _body.Background = new SolidColorBrush(canvas);
        _root.Background = new SolidColorBrush(canvas);
        _reviewRegion.Background = new SolidColorBrush(surface);
    }

    private async void ShowAbout()
    {
        var dialog = new ContentDialog
        {
            Title = "关于发票工具箱",
            Content = "版本 1.0.0\n批量识别 · 归档 · 核对\n\n办公工具箱出品",
            CloseButtonText = "关闭",
            XamlRoot = _root.XamlRoot,
        };
        await dialog.ShowAsync();
    }
}
