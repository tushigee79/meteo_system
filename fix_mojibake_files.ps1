$files = @(
  "messaging\__init__.py",
  "meteo_config\admin.py",
  "meteo_config\settings.py"
)

function Fix-Mojibake($text) {
    try {
        return [System.Text.Encoding]::UTF8.GetString(
            [System.Text.Encoding]::GetEncoding("latin1").GetBytes($text)
        )
    } catch {
        return $text
    }
}

foreach ($file in $files) {
    if (Test-Path $file) {
        Write-Host "Fixing $file"
        $raw = Get-Content $file -Raw
        $fixed = Fix-Mojibake $raw
        Set-Content $file $fixed -Encoding UTF8
    }
}
