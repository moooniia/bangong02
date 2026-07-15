using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using System;
using System.IO;
using Windows.ApplicationModel;

namespace InvoiceToolbox.WinUI;

public sealed class MainWindow : Window
{
    public static MainWindow? Instance { get; private set; }

    public MainWindow()
    {
        Instance = this;
        Title = "发票工具箱";
        EnsureDesktopShortcut();
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

    private static void EnsureDesktopShortcut()
    {
        try
        {
            var desktop = Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory);
            if (string.IsNullOrWhiteSpace(desktop)) return;

            var iconSource = Path.Combine(Package.Current.InstalledLocation.Path, "Assets", "InvoiceToolbox.ico");
            var iconFolder = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "Paz",
                "InvoiceToolbox");
            Directory.CreateDirectory(iconFolder);
            var iconTarget = Path.Combine(iconFolder, "InvoiceToolbox.ico");
            if (File.Exists(iconSource))
            {
                File.Copy(iconSource, iconTarget, true);
            }

            var shortcutPath = Path.Combine(desktop, "发票工具箱.lnk");
            var shellType = Type.GetTypeFromProgID("WScript.Shell");
            if (shellType is null) return;

            dynamic shell = Activator.CreateInstance(shellType)!;
            dynamic shortcut = shell.CreateShortcut(shortcutPath);
            shortcut.TargetPath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), "explorer.exe");
            shortcut.Arguments = $"shell:AppsFolder\\{Package.Current.Id.FamilyName}!App";
            shortcut.WorkingDirectory = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
            if (File.Exists(iconTarget))
            {
                shortcut.IconLocation = $"{iconTarget},0";
            }
            shortcut.Description = "发票工具箱";
            shortcut.Save();
        }
        catch
        {
            // Shortcut creation is a convenience, not a startup blocker.
        }
    }
}
