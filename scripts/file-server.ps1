# Chronicler File Server v2 (Hardened)
# Serves files from Dwarf Fortress directory on port 8889
# Deployed + started by vm-lifecycle.sh http-serve
#
# v2 changes:
#   - Per-request try/catch: client disconnects do not kill the server
#   - Auto-restart: if listener dies, wait 3s and restart
#   - StatusCode set before Write to avoid header-after-body errors
#   - Request counter and uptime tracking
#   - Content-Type set by file extension (not hardcoded JSON)

$dfPath = "C:\Program Files (x86)\Steam\steamapps\common\Dwarf Fortress"
$port = 8889
$requestCount = 0
$errorCount = 0
$startTime = Get-Date

Write-Host "=== Chronicler File Server v2 ===" -ForegroundColor Cyan
Write-Host "Serving: $dfPath" -ForegroundColor Cyan
Write-Host "Port:    $port" -ForegroundColor Cyan
Write-Host ""

# Outer restart loop - if listener crashes, restart after 3s
while ($true) {
    $listener = $null
    try {
        $listener = [System.Net.HttpListener]::new()
        $listener.Prefixes.Add("http://+:${port}/")
        $listener.Start()
        Write-Host "[$(Get-Date -Format HH:mm:ss)] Listening on port $port... (Ctrl+C to stop)" -ForegroundColor Green

        while ($listener.IsListening) {
            $ctx = $listener.GetContext()
            $requestCount++

            # Per-request error handling - a single bad request never kills the server
            try {
                $file = $ctx.Request.Url.AbsolutePath.TrimStart("/")
                if ([string]::IsNullOrEmpty($file)) { $file = "index" }
                $path = Join-Path $dfPath $file

                if ($file -eq "index") {
                    # Root request: return server status
                    $msg = [System.Text.Encoding]::UTF8.GetBytes("Chronicler File Server OK (requests: $requestCount)")
                    $ctx.Response.StatusCode = 200
                    $ctx.Response.ContentType = "text/plain"
                    $ctx.Response.ContentLength64 = $msg.Length
                    $ctx.Response.OutputStream.Write($msg, 0, $msg.Length)
                    Write-Host "[$(Get-Date -Format HH:mm:ss)] 200 / (status) [#$requestCount]" -ForegroundColor Green
                } elseif (Test-Path $path) {
                    $bytes = [System.IO.File]::ReadAllBytes($path)
                    $ctx.Response.StatusCode = 200

                    # Set content type by extension
                    $ext = [System.IO.Path]::GetExtension($path).ToLower()
                    switch ($ext) {
                        ".json" { $ctx.Response.ContentType = "application/json" }
                        ".xml"  { $ctx.Response.ContentType = "application/xml" }
                        ".txt"  { $ctx.Response.ContentType = "text/plain" }
                        ".log"  { $ctx.Response.ContentType = "text/plain" }
                        default { $ctx.Response.ContentType = "application/octet-stream" }
                    }

                    $ctx.Response.ContentLength64 = $bytes.Length
                    $ctx.Response.OutputStream.Write($bytes, 0, $bytes.Length)
                    $sizeMB = [math]::Round($bytes.Length / 1MB, 1)
                    Write-Host "[$(Get-Date -Format HH:mm:ss)] 200 /$file (${sizeMB} MB) [#$requestCount]" -ForegroundColor Green
                } else {
                    $msg = [System.Text.Encoding]::UTF8.GetBytes("Not found: $file")
                    $ctx.Response.StatusCode = 404
                    $ctx.Response.ContentLength64 = $msg.Length
                    $ctx.Response.OutputStream.Write($msg, 0, $msg.Length)
                    Write-Host "[$(Get-Date -Format HH:mm:ss)] 404 /$file [#$requestCount]" -ForegroundColor Red
                }
            } catch {
                # Client disconnected mid-response, file locked, or other I/O error
                $errorCount++
                Write-Host "[$(Get-Date -Format HH:mm:ss)] ERR /$file - $($_.Exception.Message) [errors: $errorCount]" -ForegroundColor Yellow
            } finally {
                # Always close the response stream, even on error
                try { $ctx.Response.OutputStream.Close() } catch { }
                try { $ctx.Response.Close() } catch { }
            }
        }

    } catch [System.Net.HttpListenerException] {
        Write-Host "[$(Get-Date -Format HH:mm:ss)] Listener error: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "  Restarting in 3 seconds..." -ForegroundColor Yellow
    } catch {
        Write-Host "[$(Get-Date -Format HH:mm:ss)] Unexpected error: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "  Restarting in 3 seconds..." -ForegroundColor Yellow
    } finally {
        if ($listener) {
            try { $listener.Stop() } catch { }
            try { $listener.Close() } catch { }
        }
    }

    # Brief pause before restart to avoid tight error loops
    $uptime = (Get-Date) - $startTime
    Write-Host "[$(Get-Date -Format HH:mm:ss)] Server recycling (uptime: $($uptime.ToString("hh\:mm\:ss")), requests: $requestCount, errors: $errorCount)" -ForegroundColor Cyan
    Start-Sleep -Seconds 3
}
