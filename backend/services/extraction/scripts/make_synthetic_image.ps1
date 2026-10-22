param([string]$OutputPath = 'venv/task-a-artifacts/synthetic_medicine_bag.png')
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$absoluteOutput = [System.IO.Path]::GetFullPath($OutputPath)
[System.IO.Directory]::CreateDirectory([System.IO.Path]::GetDirectoryName($absoluteOutput)) | Out-Null
$bitmap = [System.Drawing.Bitmap]::new(1400,1100)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$font = [System.Drawing.Font]::new('Malgun Gothic',28)
$titleFont = [System.Drawing.Font]::new('Malgun Gothic',38,[System.Drawing.FontStyle]::Bold)
try {
    $graphics.Clear([System.Drawing.Color]::White)
    $graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
    $graphics.DrawString('가상 약봉투 테스트용',[System.Drawing.Font]$titleFont,[System.Drawing.Brushes]::Black,55,40)
    $lines = @(
        '실제 환자나 실제 처방과 관계없는 합성 자료',
        '',
        '제품명: 가상제품A 100mg',
        '성분: 가상성분A 100mg',
        '복용법: 1회 1정, 하루 2회, 3일간',
        '',
        '제품명: 가상제품B 복합정',
        '성분: 가상성분B 25mg + 가상성분C 50mg',
        '복용법: 1회 2정, 하루 1회, 7일간',
        '',
        '문서 유형: 약봉투'
    )
    $y = 130
    foreach ($line in $lines) {
        $graphics.DrawString($line,$font,[System.Drawing.Brushes]::Black,55,$y)
        $y += 75
    }
    $bitmap.Save($absoluteOutput,[System.Drawing.Imaging.ImageFormat]::Png)
} finally {
    $graphics.Dispose()
    $font.Dispose()
    $titleFont.Dispose()
    $bitmap.Dispose()
}
Get-Item -LiteralPath $absoluteOutput | Select-Object FullName,Length
