# Cat & phong to mot vung cua trang scan de doc bang mat (xac minh OCR / doc bang dap an).
# usage: powershell -File tools\crop.ps1 <page.png> <y0> <y1> <x0> <x1> [scale]
#   page.png co the la duong dan tuyet doi; neu chi la ten file se tim trong $env:TEMP
param([string]$page, [int]$y0, [int]$y1, [int]$x0, [int]$x1, [double]$s = 2.0)
Add-Type -AssemblyName System.Drawing
if (-not [System.IO.Path]::IsPathRooted($page)) { $page = Join-Path $env:TEMP $page }
$stem = [System.IO.Path]::GetFileNameWithoutExtension($page)
$out = Join-Path $env:TEMP ('crop_{0}_{1}_{2}_{3}_{4}.png' -f $stem, $y0, $y1, $x0, $x1)
$img = [System.Drawing.Image]::FromFile($page)
$w = $x1 - $x0
$h = $y1 - $y0
$bmp = New-Object System.Drawing.Bitmap([int]($w * $s), [int]($h * $s))
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
$g.DrawImage($img, (New-Object System.Drawing.Rectangle(0, 0, $bmp.Width, $bmp.Height)),
             (New-Object System.Drawing.Rectangle($x0, $y0, $w, $h)),
             [System.Drawing.GraphicsUnit]::Pixel)
$bmp.Save($out, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose(); $img.Dispose()
"$out  $($bmp.Width)x$($bmp.Height)"
