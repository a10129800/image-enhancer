using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

namespace ImageEnhancerLauncher
{
    static class Program
    {
        [STAThread]
        static void Main()
        {
            try
            {
                string baseDir = AppDomain.CurrentDomain.BaseDirectory;
                string scriptPath = Path.Combine(baseDir, "src", "gui.py");

                if (!File.Exists(scriptPath))
                {
                    MessageBox.Show(
                        "找不到主程式檔案：\n" + scriptPath + "\n\n請確認專案資料夾結構是否完整（包含 src/gui.py）。",
                        "啟動失敗 - 圖片畫質提高工具",
                        MessageBoxButtons.OK,
                        MessageBoxIcon.Error
                    );
                    return;
                }

                // 優先使用 pythonw.exe (無黑視窗背景執行)
                ProcessStartInfo psi = new ProcessStartInfo();
                psi.FileName = "pythonw.exe";
                psi.Arguments = "\"" + scriptPath + "\"";
                psi.WorkingDirectory = baseDir;
                psi.UseShellExecute = false;
                psi.CreateNoWindow = true;

                try
                {
                    Process.Start(psi);
                    return;
                }
                catch
                {
                    // 若直接呼叫 pythonw.exe 失敗，嘗試透過 cmd start 呼叫
                }

                try
                {
                    ProcessStartInfo cmdPsi = new ProcessStartInfo();
                    cmdPsi.FileName = "cmd.exe";
                    cmdPsi.Arguments = "/c start \"\" pythonw \"" + scriptPath + "\"";
                    cmdPsi.WorkingDirectory = baseDir;
                    cmdPsi.UseShellExecute = false;
                    cmdPsi.CreateNoWindow = true;
                    Process.Start(cmdPsi);
                    return;
                }
                catch
                {
                }

                // 次選：嘗試一般 python.exe
                try
                {
                    ProcessStartInfo pyPsi = new ProcessStartInfo();
                    pyPsi.FileName = "python.exe";
                    pyPsi.Arguments = "\"" + scriptPath + "\"";
                    pyPsi.WorkingDirectory = baseDir;
                    pyPsi.UseShellExecute = false;
                    pyPsi.CreateNoWindow = true;
                    Process.Start(pyPsi);
                    return;
                }
                catch
                {
                }

                // 若都找不到，跳出友善提示視窗
                MessageBox.Show(
                    "系統找不到 Python 執行環境！\n\n" +
                    "請確認您的電腦已安裝 Python 3.8 以上版本，\n" +
                    "並且在安裝時勾選了『Add python.exe to PATH』（加入環境變數）。\n\n" +
                    "官方下載網址：https://www.python.org/downloads/",
                    "未檢測到 Python 環境",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Warning
                );
            }
            catch (Exception ex)
            {
                MessageBox.Show(
                    "啟動時發生未預期的錯誤：\n" + ex.Message,
                    "錯誤",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error
                );
            }
        }
    }
}
