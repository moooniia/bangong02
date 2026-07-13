using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using System;
using System.IO;

namespace InvoiceToolbox.WinUI;

public sealed class MainWindow : Window
{
    public static MainWindow? Instance { get; private set; }

    public MainWindow()
    {
        Instance = this;
        Title = "发票工具箱";
        try
        {
            var page = new MainPage();
            Content = page;
            ExtendsContentIntoTitleBar = true;
            SetTitleBar(page.TitleBarElement);
        }
        catch (Exception ex)
        {
            var log = Path.Combine(Path.GetTempPath(), "invoice_toolbox_xaml_error.txt");
            File.WriteAllText(log, ex.ToString());
            Content = new TextBlock { Text = $"XAML 加载失败\n{ex.Message}\n\n日志：{log}", Margin = new Thickness(24), TextWrapping = TextWrapping.Wrap };
        }
    }
}
