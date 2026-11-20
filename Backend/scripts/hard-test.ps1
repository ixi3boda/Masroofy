<#
.SYNOPSIS
  Hard test of the Masroofy backend: API -> PostgreSQL -> Firebase. See docs/05-hard-test-plan.md.

.DESCRIPTION
  Needs the stack running (docker compose up -d) with MAIL_PROVIDER=log, run from anywhere on Windows PowerShell 5.1+.
  Every test user is called hq<tag>...@...example.com and is deleted from Firebase and PostgreSQL at the end.
  Results: Backend/target/hard-test/results.json and results.md. Only statuses and codes are printed, never tokens.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File Backend/scripts/hard-test.ps1
  powershell -ExecutionPolicy Bypass -File Backend/scripts/hard-test.ps1 -Phase 1,4
  powershell -ExecutionPolicy Bypass -File Backend/scripts/hard-test.ps1 -SkipOutage
#>
param(
    [string]$Phase = '0,1,2,3,4,5,6,7,9,8',   # comma-separated; works with -File too
    [switch]$SkipOutage
)

$ErrorActionPreference = 'Continue'
$PhaseList = @($Phase -split '[,\s]+' | Where-Object { $_ -match '^\d$' } | ForEach-Object { [int]$_ })
Set-Location (Split-Path -Parent $PSScriptRoot)   # Backend/
try { $OutputEncoding = New-Object System.Text.UTF8Encoding($false) } catch {}
try { [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false) } catch {}
[System.Net.ServicePointManager]::DefaultConnectionLimit = 200
[System.Net.ServicePointManager]::Expect100Continue = $false
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12

function Get-EnvValue([string]$Name) {
    $m = Select-String -Path .env -Pattern "^$Name=(.*)$" | Select-Object -Last 1
    if ($m) { $m.Matches[0].Groups[1].Value.Trim() } else { '' }
}
$BackendPort = Get-EnvValue BACKEND_PORT; if (-not $BackendPort) { $BackendPort = '8080' }
$BASE = "http://localhost:$BackendPort"
$API = "$BASE/api/v1"
$DbUser = Get-EnvValue DB_USERNAME
$DbName = Get-EnvValue DB_NAME
$FbKey = Get-EnvValue FIREBASE_WEB_API_KEY
$TAG = Get-Random -Minimum 10000 -Maximum 99999
$PW = 'Sunny-Nile9'
$NEWPW = 'Fresh-Start7'

# ---------------------------------------------------------------------------------------------------------------
# HTTP (raw HttpWebRequest: UTF-8 both ways, error bodies always readable, usable inside runspaces)
# ---------------------------------------------------------------------------------------------------------------
$HttpFunction = @'
function Send-Http {
    param([string]$Method, [string]$Url, $Body = $null, [string]$ContentType = 'application/json; charset=utf-8',
          [hashtable]$Headers = @{}, [int]$TimeoutMs = 70000)
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    try {
        $req = [System.Net.HttpWebRequest]::Create($Url)
        $req.Method = $Method; $req.Timeout = $TimeoutMs; $req.ReadWriteTimeout = $TimeoutMs; $req.AllowAutoRedirect = $false
        if ($ContentType) { $req.ContentType = $ContentType }
        foreach ($k in $Headers.Keys) { $req.Headers[$k] = $Headers[$k] }
        if ($null -ne $Body -and $Method -ne 'GET' -and $Method -ne 'HEAD') {
            $bytes = [System.Text.Encoding]::UTF8.GetBytes([string]$Body)
            $req.ContentLength = $bytes.Length
            $stream = $req.GetRequestStream(); $stream.Write($bytes, 0, $bytes.Length); $stream.Close()
        } elseif ($Method -eq 'POST' -or $Method -eq 'PUT' -or $Method -eq 'PATCH') {
            $req.ContentLength = 0
        }
        $resp = $null; $err = $null
        try { $resp = $req.GetResponse() } catch [System.Net.WebException] { $resp = $_.Exception.Response; $err = $_.Exception.Message }
    } catch {
        $sw.Stop()
        return [pscustomobject]@{ Status = -1; Code = $null; Json = $null; Raw = "$($_.Exception.Message)"; Headers = $null; Ms = $sw.ElapsedMilliseconds }
    }
    if ($null -eq $resp) {
        $sw.Stop()
        return [pscustomobject]@{ Status = 0; Code = $null; Json = $null; Raw = "$err"; Headers = $null; Ms = $sw.ElapsedMilliseconds }
    }
    $reader = New-Object System.IO.StreamReader($resp.GetResponseStream(), [System.Text.Encoding]::UTF8)
    $raw = $reader.ReadToEnd(); $reader.Close()
    $status = [int]$resp.StatusCode; $hdrs = $resp.Headers; $resp.Close(); $sw.Stop()
    $json = $null
    if ($raw) { try { $json = $raw | ConvertFrom-Json } catch { } }
    $code = $null
    if ($null -ne $json -and $json -isnot [array] -and ($json.PSObject.Properties.Name -contains 'code')) { $code = [string]$json.code }
    [pscustomobject]@{ Status = $status; Code = $code; Json = $json; Raw = $raw; Headers = $hdrs; Ms = $sw.ElapsedMilliseconds }
}
'@
Invoke-Expression $HttpFunction

$Users = [ordered]@{}            # email -> list of passwords (newest last), for cleanup
$Secrets = New-Object System.Collections.Generic.List[string]   # values that must never appear in the DB
$ErrorBodies = New-Object System.Collections.Generic.List[string]

function Add-User([string]$Email, [string]$Password) {
    $e = $Email.Trim().ToLowerInvariant()
    if (-not $Users.Contains($e)) { $Users[$e] = New-Object System.Collections.Generic.List[string] }
    if (-not $Users[$e].Contains($Password)) { $Users[$e].Add($Password) }
    if (-not $Secrets.Contains($Password)) { $Secrets.Add($Password) }
}

function ConvertTo-Body($Body) {
    if ($null -eq $Body) { return $null }
    if ($Body -is [string]) { return $Body }
    ConvertTo-Json -InputObject $Body -Depth 6 -Compress
}

# Api METHOD PATH [body] [token]. Strings are sent as-is; hashtables/arrays as JSON.
function Api {
    param([string]$Method, [string]$Path, $Body = $null, [string]$Token = '', [hashtable]$Headers = @{},
          [string]$ContentType = 'application/json; charset=utf-8')
    $h = @{} + $Headers
    if ($Token) { $h['Authorization'] = "Bearer $Token" }
    $url = if ($Path -like 'http*') { $Path } else { "$API$Path" }
    $r = Send-Http -Method $Method -Url $url -Body (ConvertTo-Body $Body) -ContentType $ContentType -Headers $h
    if ($Path -eq '/auth/register' -and $r.Status -eq 201 -and $Body -is [hashtable]) { Add-User $Body.email $Body.password }
    if ($r.Status -ge 400 -and $r.Raw) { $ErrorBodies.Add($r.Raw) }
    $r
}

# ---------------------------------------------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------------------------------------------
$Results = New-Object System.Collections.Generic.List[object]
$script:CurrentPhase = ''

function Add-Result([string]$Id, [string]$Class, [string]$Case, [string]$Expected, [string]$Actual, [string]$Result,
                    [string]$Note = '', [string]$Layer = 'API') {
    $Results.Add([pscustomobject]@{ Phase = $script:CurrentPhase; Id = $Id; Class = $Class; Layer = $Layer; Case = $Case;
        Expected = $Expected; Actual = $Actual; Result = $Result; Note = $Note })
    $color = @{ PASS = 'Green'; FAIL = 'Red'; INFO = 'Yellow' }[$Result]
    Write-Host ("  [{0}] {1,-8} {2}  ->  {3} {4}" -f $Result, $Id, $Case, $Actual, $(if ($Note) { "($Note)" } else { '' })) -ForegroundColor $color
}

# Expect: response status in $Status (and code if given); a 5xx is always a failure unless expected.
function Expect {
    param([string]$Id, [string]$Class, [string]$Case, $R, [int[]]$Status, [string]$Code = '', $Extra = $true,
          [string]$Note = '', [string]$Layer = 'API')
    $statusOk = $Status -contains $R.Status
    $codeOk = (-not $Code) -or ($R.Code -eq $Code)
    $serverError = ($R.Status -ge 500 -or $R.Status -le 0) -and -not ($Status | Where-Object { $_ -ge 500 })
    $ok = $statusOk -and $codeOk -and [bool]$Extra -and -not $serverError
    if ($statusOk -and $codeOk -and -not [bool]$Extra -and -not $Note) { $Note = 'extra check failed' }
    Add-Result $Id $Class $Case ((($Status -join '/') + " $Code").Trim()) ("$($R.Status) $($R.Code)".Trim()) $(if ($ok) { 'PASS' } else { 'FAIL' }) $Note $Layer
}

function Check([string]$Id, [string]$Class, [string]$Case, $Ok, [string]$Note = '', [string]$Layer = 'DB') {
    $Ok = [bool]$Ok
    Add-Result $Id $Class $Case 'true' "$Ok" $(if ($Ok) { 'PASS' } else { 'FAIL' }) $Note $Layer
}

function Info([string]$Id, [string]$Class, [string]$Case, [string]$Actual, [string]$Note = '', [string]$Layer = 'API') {
    Add-Result $Id $Class $Case '(observation)' $Actual 'INFO' $Note $Layer
}

# ---------------------------------------------------------------------------------------------------------------
# DB, logs, Firebase, JWT helpers
# ---------------------------------------------------------------------------------------------------------------
function Sql([string]$Query) {
    $out = $Query | docker compose exec -T db psql -U $DbUser -d $DbName -qtA -v ON_ERROR_STOP=1 2>&1
    @($out | ForEach-Object { "$_" } | Where-Object { $_ -ne '' })
}
function Sql1([string]$Query) { $r = @(Sql $Query); if ($r.Count -gt 0) { "$($r[0])".Trim() } else { '' } }
function Q([string]$Value) { $Value.Replace("'", "''") }
# Text read back as hex so non-ASCII survives whatever code page the console uses.
function FromHex([string]$Hex) {
    if (-not $Hex) { return '' }
    $bytes = New-Object byte[] ($Hex.Length / 2)
    for ($i = 0; $i -lt $bytes.Length; $i++) { $bytes[$i] = [Convert]::ToByte($Hex.Substring($i * 2, 2), 16) }
    [System.Text.Encoding]::UTF8.GetString($bytes)
}

function Get-Masked([string]$Email) { $Email.Substring(0, 1) + '***' + $Email.Substring($Email.IndexOf('@')) }
function Get-DevCode([string]$Kind, [string]$Email) {
    $needle = "$Kind code for $(Get-Masked $Email): "
    for ($i = 0; $i -lt 30; $i++) {
        $line = docker compose logs --since 60m --no-log-prefix backend 2>$null | Where-Object { $_.Contains($needle) } | Select-Object -Last 1
        if ($line -and $line -match ': (\d{6}) \(') { if (-not $Secrets.Contains($Matches[1])) { $Secrets.Add($Matches[1]) }; return $Matches[1] }
        Start-Sleep -Milliseconds 400
    }
    $null
}

function Fb([string]$Op, [hashtable]$Body) {
    Send-Http -Method POST -Url "https://identitytoolkit.googleapis.com/v1/accounts:$Op" -Body (ConvertTo-Body $Body) -Headers @{ 'X-Goog-Api-Key' = $FbKey }
}
function Fb-SignIn([string]$Email, [string]$Password) { Fb signInWithPassword @{ email = $Email; password = $Password; returnSecureToken = $true } }
function Fb-Lookup([string]$IdToken) { Fb lookup @{ idToken = $IdToken } }

function ConvertFrom-B64Url([string]$s) {
    $s = $s.Replace('-', '+').Replace('_', '/')
    switch ($s.Length % 4) { 2 { $s += '==' } 3 { $s += '=' } }
    [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($s))
}
function ConvertTo-B64Url([string]$s) {
    [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($s)).TrimEnd('=').Replace('+', '-').Replace('/', '_')
}
function Get-Claims([string]$Jwt) { (ConvertFrom-B64Url ($Jwt.Split('.')[1])) | ConvertFrom-Json }
function Get-ClaimVersion([string]$Jwt) {
    $c = Get-Claims $Jwt
    if ($c.PSObject.Properties.Name -contains 'session_version') { [int]$c.session_version } else { 0 }
}

function New-Email([string]$Key) { "hq$TAG$Key@$Key$TAG.example.com".ToLowerInvariant() }

function New-Registered([string]$Key, [string]$Name = 'Hard Tester', [string]$Password = $PW) {
    $e = New-Email $Key
    $r = Api POST /auth/register @{ fullName = $Name; email = $e; password = $Password; acceptedTerms = $true }
    if ($r.Status -ne 201) { throw "setup: register $Key returned $($r.Status) $($r.Code)" }
    [pscustomobject]@{ Email = $e; Pw = $Password; Id = $r.Json.user.id; Registered = Get-Date }
}
function New-Verified([string]$Key, [string]$Name = 'Hard Tester', [string]$Password = $PW) {
    $u = New-Registered $Key $Name $Password
    $code = Get-DevCode 'Verification' $u.Email
    $v = Api POST /auth/email-verification/verify @{ email = $u.Email; code = $code }
    if ($v.Status -ne 200) { throw "setup: verify $Key returned $($v.Status) $($v.Code)" }
    $l = Api POST /auth/login @{ email = $u.Email; password = $Password }
    if ($l.Status -ne 200) { throw "setup: login $Key returned $($l.Status) $($l.Code)" }
    $u | Add-Member Access $l.Json.accessToken -PassThru | Add-Member Refresh $l.Json.refreshToken -PassThru
}
function Get-ResetToken($User) {
    $f = Api POST /auth/password/forgot @{ email = $User.Email }
    if ($f.Status -ne 202) { throw "setup: forgot returned $($f.Status) $($f.Code)" }
    $c = Get-DevCode 'Password reset' $User.Email
    $v = Api POST /auth/password/verify-code @{ email = $User.Email; code = $c }
    if ($v.Status -ne 200) { throw "setup: verify-code returned $($v.Status) $($v.Code)" }
    $Secrets.Add($v.Json.resetToken); $v.Json.resetToken
}
function Wait-Cooldown($User, [int]$Seconds = 62) {
    $left = $Seconds - ((Get-Date) - $User.Registered).TotalSeconds
    if ($left -gt 0) { Write-Host "  ...waiting $([math]::Ceiling($left)) s for the resend cooldown" -ForegroundColor DarkGray; Start-Sleep -Seconds ([math]::Ceiling($left)) }
}
function Get-DbUser([string]$Email) {
    $row = Sql1 "SELECT firebase_uid || '|' || (email_verified_at IS NOT NULL) || '|' || session_version || '|' || encode(convert_to(full_name, 'UTF8'), 'hex') FROM users WHERE email = '$(Q $Email)';"
    if (-not $row -or $row -notlike '*|*') { return $null }
    $p = $row.Split('|', 4)
    [pscustomobject]@{ Uid = $p[0]; Verified = ($p[1] -eq 'true'); Version = [int]$p[2]; Name = (FromHex $p[3]) }
}

# Fire the same kind of request N times at once (RunspacePool, common start instant).
function Invoke-Parallel([object[]]$Requests) {
    $pool = [runspacefactory]::CreateRunspacePool(1, [Math]::Max(1, $Requests.Count)); $pool.Open()
    $startAt = (Get-Date).AddMilliseconds(1500)
    $script = "param(`$Method, `$Url, `$Body, `$Token, `$StartAt)`n" + $HttpFunction + @'

while ((Get-Date) -lt $StartAt) { }
$h = @{}; if ($Token) { $h['Authorization'] = "Bearer $Token" }
Send-Http -Method $Method -Url $Url -Body $Body -Headers $h
'@
    $sb = [scriptblock]::Create($script)
    $jobs = foreach ($q in $Requests) {
        $ps = [powershell]::Create(); $ps.RunspacePool = $pool
        [void]$ps.AddScript($sb).AddArgument($q.Method).AddArgument("$API$($q.Path)").AddArgument((ConvertTo-Body $q.Body)).AddArgument($q.Token).AddArgument($startAt)
        @{ PS = $ps; Handle = $ps.BeginInvoke() }
    }
    $out = foreach ($j in $jobs) { $res = $j.PS.EndInvoke($j.Handle); $j.PS.Dispose(); $res | Select-Object -Last 1 }
    $pool.Close(); $pool.Dispose()
    $out
}
function Count-Status($Responses, [int]$Status, [string]$Code = '') {
    @($Responses | Where-Object { $_.Status -eq $Status -and (-not $Code -or $_.Code -eq $Code) }).Count
}
function Describe($Responses) {
    ($Responses | Group-Object { "$($_.Status) $($_.Code)".Trim() } | ForEach-Object { "$($_.Count)x $($_.Name)" }) -join ', '
}

# ===============================================================================================================
# Phases
# ===============================================================================================================
function Phase0 {
    $h = Send-Http GET "$BASE/actuator/health"
    Expect 'PRE-01' valid 'Backend health is UP' $h 200 '' ($h.Json.status -eq 'UP')
    $fw = Sql "SELECT version || ':' || success FROM flyway_schema_history WHERE version IS NOT NULL ORDER BY installed_rank;"
    Check 'PRE-02' valid 'Flyway V1-V3 applied successfully' (($fw -join ',') -eq '1:true,2:true,3:true') "history=$($fw -join ',')"
    Check 'PRE-03' valid '.env has DB and Firebase settings' ([bool]$DbUser -and [bool]$DbName -and $FbKey -like 'AIza*') '' 'Config'
    Check 'PRE-04' valid 'MAIL_PROVIDER=log (codes readable from the log)' ((Get-EnvValue MAIL_PROVIDER) -eq 'log') '' 'Config'
}

function Phase1 {
    $ok = @{ fullName = 'Hard Tester'; password = $PW; acceptedTerms = $true }
    function Reg([string]$Key, [hashtable]$Override) { $b = @{} + $ok; $b.email = New-Email $Key; foreach ($k in $Override.Keys) { $b[$k] = $Override[$k] }; Api POST /auth/register $b }
    function Without([string]$Key, [string]$Field) { $b = @{} + $ok; $b.email = New-Email $Key; $b.Remove($Field); Api POST /auth/register $b }
    function HasField($R, [string]$Field) { @($R.Json.fieldErrors | ForEach-Object { $_.field }) -contains $Field }

    # -- register: fullName
    $r = Reg 'r01' @{};                               Expect 'IN-01' valid 'register: valid body' $r 201 '' ($r.Json.user.emailVerified -eq $false)
    $r = Without 'r02' 'fullName';                    Expect 'IN-02' invalid 'register: fullName missing' $r 400 VALIDATION_FAILED (HasField $r fullName)
    $r = Reg 'r03' @{ fullName = $null };             Expect 'IN-03' invalid 'register: fullName null' $r 400 VALIDATION_FAILED (HasField $r fullName)
    $r = Reg 'r04' @{ fullName = '' };                Expect 'IN-04' invalid 'register: fullName empty' $r 400 VALIDATION_FAILED (HasField $r fullName)
    $r = Reg 'r05' @{ fullName = '     ' };           Expect 'IN-05' invalid 'register: fullName whitespace only' $r 400 VALIDATION_FAILED (HasField $r fullName)
    $r = Reg 'r06' @{ fullName = 'N' * 100 };         Expect 'IN-06' boundary 'register: fullName 100 chars (max)' $r 201
    $r = Reg 'r07' @{ fullName = 'N' * 101 };         Expect 'IN-07' boundary 'register: fullName 101 chars' $r 400 VALIDATION_FAILED (HasField $r fullName)
    $arabic = -join ([char[]]@(0x0645, 0x0631, 0x064A, 0x0645, 0x20, 0x0639, 0x0644, 0x064A))
    $r = Reg 'r08' @{ fullName = $arabic };           Expect 'IN-08' valid 'register: Arabic name round-trips' $r 201 '' ($r.Json.user.fullName -eq $arabic)
    $db = Get-DbUser (New-Email 'r08');               Check 'IN-08b' valid 'Arabic name stored intact in DB' ($db -and $db.Name -eq $arabic)
    $emoji = 'Mariam ' + [char]::ConvertFromUtf32(0x1F4B8)
    $r = Reg 'r09' @{ fullName = $emoji };            Expect 'IN-09' valid 'register: emoji in name round-trips' $r 201 '' ($r.Json.user.fullName -eq $emoji)
    $r = Reg 'r10' @{ fullName = 12345 };             Expect 'IN-10' type 'register: fullName is a JSON number' $r 201, 400 '' $true 'Jackson coerces numbers to text'
    $r = Reg 'r11' @{ fullName = @('a', 'b') };       Expect 'IN-11' type 'register: fullName is an array' $r 400 MALFORMED_REQUEST

    # -- register: email
    $r = Without 'r12' 'email';                       Expect 'IN-12' invalid 'register: email missing' $r 400 VALIDATION_FAILED (HasField $r email)
    foreach ($case in @(
            @('IN-13', '', 'email empty'), @('IN-14', 'plainaddress', 'email without @'),
            @('IN-15', "hq$TAG@nodot", 'email without a dot in the domain'), @('IN-16', "hq$TAG@@x.example.com", 'email with two @'),
            @('IN-17', "hq $TAG@x.example.com", 'email with a space inside'), @('IN-18', "hq$TAG@x.c", 'email TLD of 1 char'))) {
        $r = Reg 'rx' @{ email = $case[1] };          Expect $case[0] invalid "register: $($case[2])" $r 400 VALIDATION_FAILED (HasField $r email)
    }
    $messy = '  ' + (New-Email 'r19').ToUpperInvariant() + '  '
    $r = Reg 'r19' @{ email = $messy };               Expect 'IN-19' valid 'register: email upper-case with spaces is normalized' $r 201 '' ($r.Json.user.email -eq (New-Email 'r19'))
    $local = "hq${TAG}r20"; $mid = (('a' * 62 + '.') * 5).Substring(0, 254 - $local.Length - 1 - '.example.com'.Length)
    if ($mid.EndsWith('.')) { $mid = $mid.Substring(0, $mid.Length - 1) + 'a' }
    $long254 = "$local@$mid.example.com"
    $r = Reg 'r20' @{ email = $long254 };             Expect 'IN-20' boundary "register: email of 254 chars (max)" $r 201, 400 '' ($r.Status -eq 201 -or $r.Code -eq 'VALIDATION_FAILED') "len=$($long254.Length)"
    if ($r.Status -eq 201) { Add-User $long254 $PW }
    $r = Reg 'r21' @{ email = 'b' + $long254 };       Expect 'IN-21' boundary 'register: email of 255 chars' $r 400 VALIDATION_FAILED (HasField $r email)
    $idn = "hq${TAG}r22@ex" + [char]0x00E4 + "mple$TAG.com"
    $r = Reg 'r22' @{ email = $idn };                 Expect 'IN-22' boundary 'register: non-ASCII (IDN) domain' $r 201, 400 '' ($r.Status -eq 201 -or $r.Code -eq 'VALIDATION_FAILED')

    # -- register: password / terms
    $r = Without 'r23' 'password';                    Expect 'IN-23' invalid 'register: password missing' $r 400 VALIDATION_FAILED (HasField $r password)
    $r = Reg 'r24' @{ password = 'Zx9-' + ('k' * 124) }; Expect 'IN-24' boundary 'register: password 128 chars (max)' $r 201
    $r = Reg 'r25' @{ password = 'Zx9-' + ('k' * 125) }; Expect 'IN-25' boundary 'register: password 129 chars' $r 400 VALIDATION_FAILED (HasField $r password)
    $r = Without 'r26' 'acceptedTerms';               Expect 'IN-26' invalid 'register: acceptedTerms missing' $r 400 VALIDATION_FAILED (HasField $r acceptedTerms)
    $r = Reg 'r27' @{ acceptedTerms = $false };       Expect 'IN-27' invalid 'register: acceptedTerms false' $r 400 VALIDATION_FAILED (HasField $r acceptedTerms)
    $r = Reg 'r28' @{ acceptedTerms = 'yes' };        Expect 'IN-28' type 'register: acceptedTerms "yes"' $r 400 MALFORMED_REQUEST
    $r = Reg 'r29' @{ acceptedTerms = 'true' };       Expect 'IN-29' type 'register: acceptedTerms "true" (string)' $r 201, 400 '' $true 'Jackson coerces "true"'
    $r = Reg 'r30' @{ isAdmin = $true; role = 'ADMIN'; emailVerified = $true }
    Expect 'IN-30' malicious 'register: extra fields (isAdmin, role, emailVerified) are ignored' $r 201 '' ($r.Json.user.emailVerified -eq $false)

    # -- register: body shape
    $r = Api POST /auth/register '[]';                Expect 'IN-31' type 'register: body is a JSON array' $r 400 MALFORMED_REQUEST
    $r = Api POST /auth/register '';                  Expect 'IN-32' invalid 'register: empty body' $r 400 MALFORMED_REQUEST
    $r = Api POST /auth/register 'null';              Expect 'IN-33' invalid 'register: body is JSON null' $r 400 '' ($r.Code -eq 'MALFORMED_REQUEST' -or $r.Code -eq 'VALIDATION_FAILED')
    $r = Api POST /auth/register '{"fullName":"x",';  Expect 'IN-34' invalid 'register: truncated JSON' $r 400 MALFORMED_REQUEST
    $r = Api POST /auth/register '{"a":1}' -ContentType 'text/plain'; Expect 'IN-35' invalid 'register: Content-Type text/plain' $r 400 MALFORMED_REQUEST
    $r = Api POST /auth/register '{"a":1}' -ContentType ''; Expect 'IN-36' invalid 'register: no Content-Type' $r 400 MALFORMED_REQUEST
    $huge = @{ fullName = 'H' * 1000000; email = (New-Email 'r37'); password = $PW; acceptedTerms = $true }
    $r = Api POST /auth/register $huge;               Expect 'IN-37' boundary 'register: 1 MB fullName' $r 400, 413 '' $true "took $($r.Ms) ms"

    # -- login
    $m = $script:Main
    $r = Api POST /auth/login @{ email = $m.Email; password = $PW };             Expect 'IN-40' valid 'login: valid' $r 200
    $r = Api POST /auth/login @{ password = $PW };                               Expect 'IN-41' invalid 'login: email missing' $r 400 VALIDATION_FAILED
    $r = Api POST /auth/login @{ email = $m.Email };                             Expect 'IN-42' invalid 'login: password missing' $r 400 VALIDATION_FAILED
    $r = Api POST /auth/login @{ email = 'not-an-email'; password = $PW };       Expect 'IN-43' invalid 'login: malformed email' $r 400 VALIDATION_FAILED
    $r = Api POST /auth/login @{ email = $m.Email; password = 'x' * 129 };       Expect 'IN-44' boundary 'login: password 129 chars' $r 400 VALIDATION_FAILED
    $r = Api POST /auth/login @{ email = ' ' + $m.Email.ToUpperInvariant() + ' '; password = $PW }; Expect 'IN-45' valid 'login: email upper-case with spaces' $r 200
    $r = Api POST /auth/login @{ email = $m.Email; password = " $PW " };         Expect 'IN-46' invalid 'login: password with surrounding spaces (not trimmed)' $r 401 INVALID_CREDENTIALS
    $r = Api POST /auth/login @{ email = $m.Email; password = $PW.ToLowerInvariant() }; Expect 'IN-47' invalid 'login: password in wrong case' $r 401 INVALID_CREDENTIALS

    # -- verify / verify-code: code format (unknown email, so no attempts are burned)
    $nobody = New-Email 'nobody'
    foreach ($case in @(@('IN-50', '123', '3 digits'), @('IN-51', '12345678901', '11 digits'), @('IN-52', '12ab56', 'letters'),
            @('IN-53', '', 'empty'), @('IN-54', ([string][char]0x0661 * 6), 'Arabic-Indic digits'))) {
        $r = Api POST /auth/email-verification/verify @{ email = $nobody; code = $case[1] }
        Expect $case[0] invalid "verify: code $($case[2])" $r 400 VALIDATION_FAILED
    }
    $r = Api POST /auth/email-verification/verify @{ email = $nobody; code = ' 123456 ' }; Expect 'IN-55' boundary 'verify: code with spaces is trimmed (unknown email)' $r 400 INVALID_OR_EXPIRED_CODE
    $r = Api POST /auth/email-verification/verify @{ email = $nobody; code = 123456 };     Expect 'IN-56' type 'verify: code as JSON number' $r 400 '' $true 'coerced; unknown email'
    $r = Api POST /auth/password/verify-code @{ email = $nobody; code = '1234' };         Expect 'IN-57' boundary 'verify-code: 4-digit code (min) on unknown email' $r 400 INVALID_OR_EXPIRED_CODE
    $r = Api POST /auth/password/verify-code @{ code = '123456' };                         Expect 'IN-58' invalid 'verify-code: email missing' $r 400 VALIDATION_FAILED

    # -- resend / forgot
    $r = Api POST /auth/email-verification/resend @{ email = 'bad' };   Expect 'IN-60' invalid 'resend: malformed email' $r 400 VALIDATION_FAILED
    $r = Api POST /auth/email-verification/resend @{};                  Expect 'IN-61' invalid 'resend: email missing' $r 400 VALIDATION_FAILED
    $r = Api POST /auth/password/forgot @{ email = 'x' * 250 + '@a.io' }; Expect 'IN-62' boundary 'forgot: email over 254 chars' $r 400 VALIDATION_FAILED
    $r = Api POST /auth/password/forgot @{ email = $nobody };           Expect 'IN-63' valid 'forgot: unknown but valid email' $r 202

    # -- refresh
    $r = Api POST /auth/token/refresh @{};                              Expect 'IN-70' invalid 'refresh: token missing' $r 400 VALIDATION_FAILED
    $r = Api POST /auth/token/refresh @{ refreshToken = '' };           Expect 'IN-71' invalid 'refresh: token empty' $r 400 VALIDATION_FAILED
    $r = Api POST /auth/token/refresh @{ refreshToken = 'r' * 2049 };   Expect 'IN-72' boundary 'refresh: token 2049 chars' $r 400 VALIDATION_FAILED
    $r = Api POST /auth/token/refresh @{ refreshToken = 'garbage' };    Expect 'IN-73' invalid 'refresh: garbage token' $r 401 INVALID_REFRESH_TOKEN

    # -- reset
    $r = Api POST /auth/password/reset @{ newPassword = $NEWPW; confirmPassword = $NEWPW };                       Expect 'IN-80' invalid 'reset: resetToken missing' $r 400 VALIDATION_FAILED
    $r = Api POST /auth/password/reset @{ resetToken = 't' * 257; newPassword = $NEWPW; confirmPassword = $NEWPW }; Expect 'IN-81' boundary 'reset: resetToken 257 chars' $r 400 VALIDATION_FAILED
    $r = Api POST /auth/password/reset @{ resetToken = 'fake'; newPassword = $NEWPW };                           Expect 'IN-82' invalid 'reset: confirmPassword missing' $r 400 VALIDATION_FAILED
    $r = Api POST /auth/password/reset @{ resetToken = 'fake'; newPassword = $NEWPW; confirmPassword = 'Other-pass9' }; Expect 'IN-83' invalid 'reset: passwords differ (checked before the token)' $r 400 PASSWORDS_DO_NOT_MATCH
    $r = Api POST /auth/password/reset @{ resetToken = 'fake'; newPassword = $NEWPW; confirmPassword = $NEWPW }; Expect 'IN-84' invalid 'reset: unknown token' $r 400 INVALID_RESET_TOKEN
}

function Phase2 {
    function Weak([string]$Id, [string]$Case, [string]$Password, [string[]]$Rules, [string]$Name = 'Mariam Ali', [string]$Email = (New-Email 'pw')) {
        $r = Api POST /auth/register @{ fullName = $Name; email = $Email; password = $Password; acceptedTerms = $true }
        $got = @($r.Json.fieldErrors | ForEach-Object { $_.code } | Sort-Object)
        $same = (($got -join ',') -eq (($Rules | Sort-Object) -join ','))
        Expect $Id weak $Case $r 400 WEAK_PASSWORD $same "rules=$($got -join ',')"
    }
    Weak 'PW-01' 'too short (7)' 'short1!' @('MIN_LENGTH')
    Weak 'PW-02' 'letters only (and a straight sequence)' 'abcdefgh' @('NUMBER_OR_SYMBOL', 'COMMON_PASSWORD')
    Weak 'PW-03' 'short and letters only' 'abcdefg' @('MIN_LENGTH', 'NUMBER_OR_SYMBOL')
    Weak 'PW-04' 'contains first name' 'Mariam-2025' @('NO_PERSONAL_INFO')
    Weak 'PW-05' 'contains first name in other case' 'mARIAM2025x' @('NO_PERSONAL_INFO')
    Weak 'PW-06' 'contains 3-letter last name' 'xxali9999' @('NO_PERSONAL_INFO')
    Weak 'PW-07' 'breaks three rules at once' 'mariam' @('MIN_LENGTH', 'NUMBER_OR_SYMBOL', 'NO_PERSONAL_INFO')
    Weak 'PW-08' 'contains a piece of the email (sara)' 'Sara-7700' @('NO_PERSONAL_INFO') 'Hard Tester' "hq$TAG.sara_ahmed@pq$TAG.example.com"
    Weak 'PW-09' 'contains the whole email local part' "hq${TAG}pw9!" @('NO_PERSONAL_INFO') 'Hard Tester'
    $r = Api POST /auth/register @{ fullName = 'Mariam Ali'; email = (New-Email 'pw'); password = 'mariam'; acceptedTerms = $true }
    Check 'PW-10' weak 'details.failedRules equals fieldErrors codes' ((@($r.Json.details.failedRules | Sort-Object) -join ',') -eq (@($r.Json.fieldErrors.code | Sort-Object) -join ',')) '' 'API'
    $r = Api POST /auth/register @{ fullName = 'Hard Tester'; email = (New-Email 'pw'); password = '        '; acceptedTerms = $true }
    Expect 'PW-11' weak '8 spaces' $r 400 VALIDATION_FAILED
    $r = Api POST /auth/register @{ fullName = 'Hard Tester'; email = (New-Email 'pw'); password = 'a1' * 65; acceptedTerms = $true }
    Expect 'PW-12' boundary '130 chars hits the size limit first' $r 400 VALIDATION_FAILED

    $r = Api POST /auth/register @{ fullName = 'Al Bo'; email = (New-Email 'p13'); password = 'AlBo-1234'; acceptedTerms = $true }
    Expect 'PW-13' valid '2-letter name parts are allowed in the password' $r 201
    Weak 'PW-14' 'one repeated symbol' '!!!!!!!!' @('COMMON_PASSWORD') 'Hard Tester'
    Weak 'PW-15' 'common word + digit' 'password1' @('COMMON_PASSWORD') 'Hard Tester'
    Weak 'PW-16' 'digit sequence' '12345678' @('COMMON_PASSWORD') 'Hard Tester'
    Weak 'PW-16b' 'keyboard row + symbol' 'Qwerty123!' @('COMMON_PASSWORD') 'Hard Tester'
    $r = Api POST /auth/register @{ fullName = 'Hard Tester'; email = (New-Email 'p17'); password = ('abcdefg' + [char]0x0663); acceptedTerms = $true }
    if ($r.Status -eq 201) { Info 'PW-17' weak 'letters + one Arabic-Indic digit is accepted' "$($r.Status)" 'counts as a number; not a common pattern' }
    else { Expect 'PW-17' weak 'letters + one Arabic-Indic digit' $r 400 WEAK_PASSWORD }

    # Same rules on /password/reset, reported against newPassword.
    $u = New-Verified 'pr' 'Mariam Ali'
    $token = Get-ResetToken $u
    function Do-Reset([string]$New, [string]$Confirm = $New) { Api POST /auth/password/reset @{ resetToken = $token; newPassword = $New; confirmPassword = $Confirm } }
    $r = Do-Reset 'abcdefgh';    Expect 'PW-20' weak 'reset: letters only' $r 400 WEAK_PASSWORD ((@($r.Json.fieldErrors.field) | Select-Object -Unique) -eq 'newPassword')
    $r = Do-Reset 'Mariam-2025'; Expect 'PW-21' weak 'reset: contains the name' $r 400 WEAK_PASSWORD (@($r.Json.fieldErrors.code) -contains 'NO_PERSONAL_INFO')
    $r = Do-Reset $PW;           Expect 'PW-22' weak 'reset: same as the current password' $r 400 PASSWORD_REUSED
    $r = Do-Reset $NEWPW 'Fresh-Start8'; Expect 'PW-23' invalid 'reset: confirmation differs' $r 400 PASSWORDS_DO_NOT_MATCH
    $r = Do-Reset $NEWPW;        Expect 'PW-24' valid 'reset: strong new password' $r 200
    if ($r.Status -eq 200) { Add-User $u.Email $NEWPW }
}

function Phase3 {
    $F = New-Registered 'fa'; $G = New-Registered 'fg'; $H = New-Registered 'fh'
    $d = Get-DbUser $F.Email
    Check 'FL-01' state 'register creates an unverified DB row with session_version 0' ($d -and -not $d.Verified -and $d.Version -eq 0)
    $s = Fb-SignIn $F.Email $F.Pw
    Check 'FL-02' state 'Firebase account exists, same uid as the DB row' ($s.Status -eq 200 -and $s.Json.localId -eq $d.Uid) '' 'Firebase'
    $look = Fb-Lookup $s.Json.idToken
    Check 'FL-03' state 'Firebase emailVerified is false before verifying' ($look.Json.users[0].emailVerified -eq $false) '' 'Firebase'
    $r = Api POST /auth/login @{ email = $F.Email; password = $F.Pw }; Expect 'FL-04' state 'login before verifying' $r 403 EMAIL_NOT_VERIFIED

    $r = Api POST /auth/password/forgot @{ email = $F.Email };   Expect 'FL-05' state 'forgot works for an unverified user' $r 202
    $rc = Get-DevCode 'Password reset' $F.Email; $vc = Get-DevCode 'Verification' $F.Email
    $r = Api POST /auth/email-verification/verify @{ email = $F.Email; code = $rc }; Expect 'FL-06' state 'cross-purpose: reset code used to verify the email' $r 400 INVALID_CODE
    $r = Api POST /auth/password/verify-code @{ email = $F.Email; code = $vc };       Expect 'FL-07' state 'cross-purpose: verification code used as reset code' $r 400 INVALID_CODE
    $r = Api POST /auth/email-verification/verify @{ email = $F.Email; code = $vc };  Expect 'FL-08' valid 'verify with the right code (after 1 wrong try)' $r 200
    Check 'FL-09' state 'DB marks the user verified' ((Get-DbUser $F.Email).Verified)
    $look = Fb-Lookup (Fb-SignIn $F.Email $F.Pw).Json.idToken
    Check 'FL-10' state 'Firebase emailVerified is now true' ($look.Json.users[0].emailVerified -eq $true) '' 'Firebase'
    $r = Api POST /auth/email-verification/verify @{ email = $F.Email; code = $vc };  Expect 'FL-11' state 'verify again' $r 409 EMAIL_ALREADY_VERIFIED

    $l = Api POST /auth/login @{ email = $F.Email; password = $F.Pw }; Expect 'FL-12' valid 'login after verifying' $l 200
    $a1 = $l.Json.accessToken; $r1 = $l.Json.refreshToken
    Check 'FL-13' state 'refresh token is sealed (<version>.<hmac>.<token>)' ($r1 -match '^\d+\.[0-9a-f]{64}\..+') '' 'API'
    $r = Api POST /auth/token/refresh @{ refreshToken = $r1 }; Expect 'FL-14' valid 'refresh' $r 200
    if ($r.Status -eq 200) { $a1 = $r.Json.accessToken; $r1 = $r.Json.refreshToken }
    $me = Api GET /users/me $null $a1
    Expect 'FL-15' valid 'GET /users/me matches the DB' $me 200 '' ($me.Json.email -eq $F.Email -and $me.Json.fullName -eq 'Hard Tester' -and $me.Json.baseCurrency -eq 'EGP')

    $codeH = Get-DevCode 'Verification' $H.Email
    $r = Api POST /auth/email-verification/verify @{ email = $G.Email; code = $codeH }; Expect 'FL-16' state "another user's code" $r 400 INVALID_CODE
    $r = Api POST /auth/password/verify-code @{ email = $H.Email; code = '123456' };    Expect 'FL-17' state 'verify-code without asking for a reset' $r 400 INVALID_OR_EXPIRED_CODE

    $r = Api POST /auth/password/verify-code @{ email = $F.Email; code = $rc }; Expect 'FL-18' valid 'reset code still valid after a cross-purpose miss' $r 200
    $rt = $r.Json.resetToken; $Secrets.Add($rt)
    Start-Sleep -Milliseconds 1200
    $r = Api POST /auth/password/reset @{ resetToken = $rt; newPassword = $NEWPW; confirmPassword = $NEWPW }; Expect 'FL-19' valid 'reset password' $r 200
    if ($r.Status -eq 200) { Add-User $F.Email $NEWPW }
    $r = Api POST /auth/password/reset @{ resetToken = $rt; newPassword = 'Fresh-Start8'; confirmPassword = 'Fresh-Start8' }; Expect 'FL-20' state 'reuse the reset token' $r 400 INVALID_RESET_TOKEN
    $r = Api GET /users/me $null $a1;                                Expect 'FL-21' state 'access token from before the reset' $r 401 UNAUTHORIZED
    $r = Api POST /auth/token/refresh @{ refreshToken = $r1 };       Expect 'FL-22' state 'refresh token from before the reset' $r 401 INVALID_REFRESH_TOKEN
    $r = Api POST /auth/login @{ email = $F.Email; password = $F.Pw }; Expect 'FL-23' state 'old password after reset' $r 401 INVALID_CREDENTIALS
    $l = Api POST /auth/login @{ email = $F.Email; password = $NEWPW }; Expect 'FL-24' valid 'new password after reset' $l 200
    $dbv = (Get-DbUser $F.Email).Version
    Check 'FL-25' state 'session_version is 1 in DB and in the new token' ($dbv -eq 1 -and (Get-ClaimVersion $l.Json.accessToken) -eq 1) "db=$dbv" 'DB+Firebase'

    $r = Api POST /auth/logout $null $l.Json.accessToken;           Expect 'FL-26' valid 'logout' $r 204
    $r = Api GET /users/me $null $l.Json.accessToken;               Expect 'FL-27' state 'access token after logout' $r 401 UNAUTHORIZED
    $r = Api POST /auth/token/refresh @{ refreshToken = $l.Json.refreshToken }; Expect 'FL-28' state 'refresh token after logout' $r 401 INVALID_REFRESH_TOKEN
    $l2 = Api POST /auth/login @{ email = $F.Email; password = $NEWPW }
    $r = Api GET /users/me $null $l2.Json.accessToken;              Expect 'FL-29' valid 'log in again right after logout' $r 200
    Check 'FL-30' state 'session_version is 2 after reset + logout' ((Get-DbUser $F.Email).Version -eq 2)

    # Reset also verifies an unverified email (H never verified).
    $tok = Get-ResetToken $H
    $r = Api POST /auth/password/reset @{ resetToken = $tok; newPassword = $NEWPW; confirmPassword = $NEWPW }; Expect 'FL-31' state 'reset for an unverified user' $r 200
    if ($r.Status -eq 200) { Add-User $H.Email $NEWPW }
    $r = Api POST /auth/login @{ email = $H.Email; password = $NEWPW }; Expect 'FL-32' state 'that user can now log in (reset proved the inbox)' $r 200
    Check 'FL-33' state 'DB and Firebase both say verified' ((Get-DbUser $H.Email).Verified -and (Fb-Lookup (Fb-SignIn $H.Email $NEWPW).Json.idToken).Json.users[0].emailVerified) '' 'DB+Firebase'

    # A new code cancels the old one (needs the 60 s cooldown).
    $old = Get-DevCode 'Verification' $G.Email
    Wait-Cooldown $G
    $r = Api POST /auth/email-verification/resend @{ email = $G.Email }; Expect 'FL-34' valid 'resend after the cooldown' $r 202
    Start-Sleep -Milliseconds 800
    $new = Get-DevCode 'Verification' $G.Email
    $r = Api POST /auth/email-verification/verify @{ email = $G.Email; code = $old }; Expect 'FL-35' state 'old code after a resend' $r 400 INVALID_CODE ($old -ne $new)
    $r = Api POST /auth/email-verification/verify @{ email = $G.Email; code = $new }; Expect 'FL-36' valid 'new code after a resend' $r 200
}

function Phase4 {
    $m = $script:Main
    $l = Api POST /auth/login @{ email = $m.Email; password = $PW }; $tok = $l.Json.accessToken; $sealed = $l.Json.refreshToken
    $r = Api GET /users/me;                                                  Expect 'TK-01' invalid 'no Authorization header' $r 401 UNAUTHORIZED
    $r = Api GET /users/me -Headers @{ Authorization = 'Bearer ' };          Expect 'TK-02' invalid 'Bearer with no token' $r 401 UNAUTHORIZED
    $r = Api GET /users/me -Headers @{ Authorization = "Bearer    $tok" };   Expect 'TK-03' boundary 'Bearer + extra spaces + valid token' $r 200, 401
    $r = Api GET /users/me $null 'garbage.garbage.garbage';                  Expect 'TK-04' invalid 'garbage JWT' $r 401 UNAUTHORIZED
    $r = Api GET /users/me -Headers @{ Authorization = "Basic $tok" };       Expect 'TK-05' invalid 'Basic scheme' $r 401 UNAUTHORIZED
    $r = Api GET /users/me -Headers @{ Authorization = "bEaReR $tok" };      Expect 'TK-06' valid 'scheme is case-insensitive' $r 200

    $parts = $tok.Split('.'); $claims = Get-Claims $tok
    $claims.user_id = 'attacker'; $claims.sub = 'attacker'; $claims.email = 'attacker@example.com'
    $forged = $parts[0] + '.' + (ConvertTo-B64Url ($claims | ConvertTo-Json -Compress)) + '.' + $parts[2]
    $r = Api GET /users/me $null $forged;                                    Expect 'TK-07' malicious 'payload changed, signature kept' $r 401 UNAUTHORIZED
    $none = (ConvertTo-B64Url '{"alg":"none","typ":"JWT"}') + '.' + $parts[1] + '.'
    $r = Api GET /users/me $null $none;                                      Expect 'TK-08' malicious 'alg=none JWT' $r 401 UNAUTHORIZED
    $r = Api GET "/users/me?access_token=$tok";                              Expect 'TK-09' malicious 'token in the query string is ignored' $r 401 UNAUTHORIZED
    $r = Api GET /users/me $null $sealed;                                    Expect 'TK-10' malicious 'refresh token used as a bearer token' $r 401 UNAUTHORIZED
    Check 'TK-11' state 'session_version claim equals DB' ((Get-ClaimVersion $tok) -eq (Get-DbUser $m.Email).Version) '' 'DB+Firebase'

    # Unverified user's genuine Firebase token.
    $u = New-Registered 'tu'
    $fs = Fb-SignIn $u.Email $u.Pw
    $r = Api GET /users/me $null $fs.Json.idToken;                           Expect 'TK-12' state 'unverified user token on /users/me' $r 403 EMAIL_NOT_VERIFIED
    $r = Api POST /auth/logout $null $fs.Json.idToken;                       Expect 'TK-13' state 'unverified user may still log out' $r 204

    # Firebase account with no Masroofy profile.
    $ze = New-Email 'tz'
    $z = Fb signUp @{ email = $ze; password = $PW; returnSecureToken = $true }
    if ($z.Status -eq 200) { Add-User $ze $PW }
    $r = Api GET /users/me $null $z.Json.idToken;                            Expect 'TK-14' malicious 'Firebase user without a DB profile on /users/me' $r 401 UNAUTHORIZED
    $r = Api POST /auth/logout $null $z.Json.idToken;                        Expect 'TK-15' malicious 'Firebase user without a DB profile logs out' $r 401 UNAUTHORIZED
    $r = Api POST /auth/login @{ email = $ze; password = $PW };              Expect 'TK-16' malicious 'Firebase user without a DB profile logs in' $r 401 INVALID_CREDENTIALS

    # Refresh-token tampering.
    $raw = (Fb-SignIn $m.Email $PW).Json.refreshToken
    $r = Api POST /auth/token/refresh @{ refreshToken = $raw };              Expect 'TK-20' malicious 'raw (unsealed) Firebase refresh token' $r 401 INVALID_REFRESH_TOKEN
    $p = $sealed.Split('.', 3)
    $r = Api POST /auth/token/refresh @{ refreshToken = "99.$($p[1]).$($p[2])" }; Expect 'TK-21' malicious 'sealed token with the version raised' $r 401 INVALID_REFRESH_TOKEN
    $flip = if ($p[1][0] -eq 'a') { 'b' } else { 'a' }
    $r = Api POST /auth/token/refresh @{ refreshToken = "$($p[0]).$flip$($p[1].Substring(1)).$($p[2])" }; Expect 'TK-22' malicious 'sealed token with the HMAC altered' $r 401 INVALID_REFRESH_TOKEN
    $r = Api POST /auth/token/refresh @{ refreshToken = "$($p[0]).$($p[1]).$raw" }; Expect 'TK-23' malicious 'seal from one session + Firebase token of another' $r 401 INVALID_REFRESH_TOKEN
    $r = Api POST /auth/token/refresh @{ refreshToken = $sealed };           Expect 'TK-24' valid 'untouched sealed token still works' $r 200
}

function Phase5 {
    $m = $script:Main
    $tok = (Api POST /auth/login @{ email = $m.Email; password = $PW }).Json.accessToken

    # SQL injection / XSS payloads
    $r = Api POST /auth/login @{ email = "x'or'1'='1@x.example.com"; password = "' OR 1=1--" }; Expect 'SEC-01' malicious "SQL injection in login" $r 401 INVALID_CREDENTIALS
    # Payloads with ; or () are not valid email characters, so validation rejects them before any SQL runs.
    $r = Api POST /auth/password/forgot @{ email = "x';DROP/**/TABLE/**/users;--@x.example.com" }
    Expect 'SEC-02' malicious 'SQL injection in forgot' $r 202, 400 '' ($r.Status -eq 202 -or $r.Code -eq 'VALIDATION_FAILED')
    $r = Api POST /auth/password/forgot @{ email = "x'or'1'='1@x.example.com" }
    Expect 'SEC-02b' malicious "SQL quote payload that passes email validation (forgot)" $r 202
    $r = Api POST /auth/email-verification/verify @{ email = "a'||pg_sleep(5)||'@x.example.com"; code = '123456' }
    Expect 'SEC-03' malicious 'time-based SQL injection in verify (pg_sleep)' $r 400 '' ($r.Ms -lt 4000 -and ($r.Code -eq 'INVALID_OR_EXPIRED_CODE' -or $r.Code -eq 'VALIDATION_FAILED')) "took $($r.Ms) ms; $($r.Code)"
    $evil = "<script>alert(1)</script>'); DROP TABLE users;--"
    $r = Api POST /auth/register @{ fullName = $evil; email = (New-Email 'sx'); password = $PW; acceptedTerms = $true }
    Expect 'SEC-04' malicious 'XSS + SQL in fullName is stored as plain text' $r 201 '' ($r.Json.user.fullName -eq $evil)
    Check 'SEC-05' malicious 'users table intact and the name stored verbatim' ((Get-DbUser (New-Email 'sx')).Name -eq $evil -and [int](Sql1 'SELECT count(*) FROM users;') -gt 0)
    Check 'SEC-06' malicious 'JSON responses use Content-Type application/json + nosniff' ($r.Headers['Content-Type'] -like 'application/json*' -and $r.Headers['X-Content-Type-Options'] -eq 'nosniff') '' 'API'

    # Path tricks
    foreach ($case in @(@('SEC-10', '/users/me/', 'trailing slash'), @('SEC-11', '//users/me', 'double slash'),
            @('SEC-12', '/users/%2e%2e/users/me', 'encoded ..'), @('SEC-13', '/users/me;jsessionid=x', 'path parameter'),
            @('SEC-14', '/users/me%00', 'null byte'), @('SEC-15', '/../actuator/env', 'dot-dot to actuator'))) {
        $r = Api GET $case[1] $null $tok
        Expect $case[0] malicious "path trick: $($case[2])" $r 400, 401, 403, 404 '' ($r.Status -ne 200)
    }

    # Method fuzzing
    $paths = '/auth/register', '/auth/login', '/auth/token/refresh', '/auth/password/forgot', '/auth/password/reset'
    $bad = 0; $seen = @()
    foreach ($p in $paths) { foreach ($verb in 'GET', 'PUT', 'DELETE', 'PATCH') {
            $r = Api $verb $p '{}'
            $seen += "$($r.Status)"; if ($r.Status -ne 405) { $bad++ } } }
    Check 'SEC-20' malicious 'GET/PUT/DELETE/PATCH on auth endpoints -> 405' ($bad -eq 0) "statuses: $(($seen | Group-Object | ForEach-Object { "$($_.Count)x$($_.Name)" }) -join ' ')" 'API'
    $r = Api DELETE /users/me $null $tok;            Expect 'SEC-21' malicious 'DELETE /users/me with a token' $r 405 METHOD_NOT_ALLOWED
    $r = Api PUT /users/me '{"fullName":"x"}' $tok;  Expect 'SEC-22' malicious 'PUT /users/me with a token' $r 405 METHOD_NOT_ALLOWED

    # Exposure
    $r = Send-Http GET "$BASE/actuator/env";                          Expect 'SEC-30' malicious '/actuator/env without a token' $r 401, 404
    $r = Send-Http GET "$BASE/actuator/env" -Headers @{ Authorization = "Bearer $tok" }; Expect 'SEC-31' malicious '/actuator/env with a token (not exposed)' $r 404
    $r = Send-Http GET "$BASE/actuator/beans" -Headers @{ Authorization = "Bearer $tok" }; Expect 'SEC-32' malicious '/actuator/beans with a token (not exposed)' $r 404
    $r = Send-Http GET "$BASE/v3/api-docs"
    Info 'SEC-33' info 'OpenAPI docs are public' "$($r.Status)" 'by design while SWAGGER_ENABLED=true; set false in production'

    # CORS
    $r = Send-Http OPTIONS "$API/auth/login" -ContentType '' -Headers @{ Origin = 'https://evil.example'; 'Access-Control-Request-Method' = 'POST' }
    Expect 'SEC-40' malicious 'CORS preflight from an unknown origin is refused' $r 403 '' (-not $r.Headers['Access-Control-Allow-Origin'])
    $r = Send-Http POST "$API/auth/login" (ConvertTo-Body @{ email = $m.Email; password = 'x' }) -Headers @{ Origin = 'https://evil.example' }
    Expect 'SEC-41' malicious 'cross-origin POST gets no Allow-Origin header' $r 401, 403 '' (-not $r.Headers['Access-Control-Allow-Origin'])

    # Headers and leaks
    $r = Api GET /users/me $null $tok
    Check 'SEC-50' info 'security headers on /users/me (nosniff, X-Frame-Options DENY, no-store)' ($r.Headers['X-Content-Type-Options'] -eq 'nosniff' -and $r.Headers['X-Frame-Options'] -eq 'DENY' -and $r.Headers['Cache-Control'] -like '*no-store*') '' 'API'
    Check 'SEC-51' info 'no Server / X-Powered-By version banner' (-not $r.Headers['X-Powered-By'] -and -not ($r.Headers['Server'] -match '\d')) "Server=$($r.Headers['Server'])" 'API'

    # Account enumeration
    $known = New-Verified 'se'; $unknown = New-Email 'seunknown'
    $k1 = Api POST /auth/password/forgot @{ email = $known.Email }; $u1 = Api POST /auth/password/forgot @{ email = $unknown }
    $same = ($k1.Status -eq $u1.Status) -and ($k1.Json.codeLength -eq $u1.Json.codeLength) -and ($k1.Json.expiresInSeconds -eq $u1.Json.expiresInSeconds) -and ($k1.Json.resendAvailableInSeconds -eq $u1.Json.resendAvailableInSeconds)
    Check 'SEC-60' enumeration 'forgot: first answer identical for known and unknown emails' $same "known=$($k1.Status) unknown=$($u1.Status)" 'API'
    $k2 = Api POST /auth/password/forgot @{ email = $known.Email }; $u2 = Api POST /auth/password/forgot @{ email = $unknown }
    Check 'SEC-61' enumeration 'forgot: second answer identical for known and unknown emails' ($k2.Status -eq $u2.Status) "known=$($k2.Status) $($k2.Code), unknown=$($u2.Status)" 'API'
    $su = New-Registered 'su'
    $k3 = Api POST /auth/email-verification/resend @{ email = $su.Email }; $u3 = Api POST /auth/email-verification/resend @{ email = $unknown }
    Info 'SEC-62a' enumeration 'resend right after sign-up vs unknown email (first call)' "known=$($k3.Status) $($k3.Code), unknown=$($u3.Status)" 'sign-up just sent a code; register itself already answers 409 for taken emails'
    $k4 = Api POST /auth/email-verification/resend @{ email = $su.Email }; $u4 = Api POST /auth/email-verification/resend @{ email = $unknown }
    Check 'SEC-62' enumeration 'resend: second answer identical for an unverified account and an unknown email' ($k4.Status -eq $u4.Status -and $k4.Code -eq $u4.Code) "known=$($k4.Status) $($k4.Code), unknown=$($u4.Status) $($u4.Code)" 'API'
    $r = Api POST /auth/register @{ fullName = 'Hard Tester'; email = $known.Email; password = $PW; acceptedTerms = $true }
    Info 'SEC-63' enumeration 'register reveals an existing email' "$($r.Status) $($r.Code)" 'by design (screen 01-02 must say the email is taken)'
    $tu = @(1..5 | ForEach-Object { (Api POST /auth/login @{ email = (New-Email "ux$_"); password = 'Wrong-pass1' }).Ms })
    $tk = @(1..5 | ForEach-Object { (Api POST /auth/login @{ email = $known.Email; password = 'Wrong-pass1' }).Ms })
    Info 'SEC-64' enumeration 'login timing: unknown email vs wrong password (avg ms)' ("{0:N0} vs {1:N0}" -f ($tu | Measure-Object -Average).Average, ($tk | Measure-Object -Average).Average) 'both answered by Firebase'

    # Error bodies must not leak internals.
    $leaky = @($ErrorBodies | Where-Object { $_ -match 'Exception|at com\.|org\.springframework|java\.|SQLState|PSQL|postgres|stack' })
    Check 'SEC-70' info "no stack traces or class names in $($ErrorBodies.Count) error bodies so far" ($leaky.Count -eq 0) $(if ($leaky) { $leaky[0].Substring(0, [Math]::Min(120, $leaky[0].Length)) } else { '' }) 'API'
    $shape = @($ErrorBodies | Where-Object { try { $j = $_ | ConvertFrom-Json; -not ($j.code -and $j.status -and $j.path -and $j.timestamp) } catch { $true } })
    $paths = @($shape | ForEach-Object { try { ($_ | ConvertFrom-Json).path } catch { '(not JSON)' } } | Select-Object -Unique)
    Check 'SEC-71' info 'every error body has the documented shape (timestamp, status, code, path)' ($shape.Count -eq 0) $(if ($shape) { "$($shape.Count) bodies without 'code' (Spring default shape) on: $($paths -join ', ')" } else { '' }) 'API'
}

function Phase6 {
    $c4 = New-Registered 'c4'    # registered first so its cooldown runs out while the other cases run

    $email = New-Email 'c1'
    $res = Invoke-Parallel (1..10 | ForEach-Object { @{ Method = 'POST'; Path = '/auth/register'; Body = @{ fullName = 'Race Tester'; email = $email; password = $PW; acceptedTerms = $true } } })
    if ((Count-Status $res 201) -ge 1) { Add-User $email $PW }
    Check 'CC-01' concurrent '10 parallel sign-ups with one email -> exactly one 201' ((Count-Status $res 201) -eq 1 -and @($res | Where-Object { $_.Status -ge 500 }).Count -eq 0) (Describe $res) 'API'
    Check 'CC-02' concurrent '...and exactly one DB row' ((Sql1 "SELECT count(*) FROM users WHERE email = '$email';") -eq '1')

    $c2 = New-Registered 'c2'; $code = Get-DevCode 'Verification' $c2.Email
    $res = Invoke-Parallel (1..10 | ForEach-Object { @{ Method = 'POST'; Path = '/auth/email-verification/verify'; Body = @{ email = $c2.Email; code = $code } } })
    Check 'CC-03' concurrent '10 parallel verifies with the right code -> exactly one 200' ((Count-Status $res 200) -eq 1 -and @($res | Where-Object { $_.Status -ge 500 }).Count -eq 0) (Describe $res) 'API'

    $c3 = New-Registered 'c3'; $right = Get-DevCode 'Verification' $c3.Email
    $wrong = if ($right -eq '000000') { '111111' } else { '000000' }
    $res = Invoke-Parallel (1..30 | ForEach-Object { @{ Method = 'POST'; Path = '/auth/email-verification/verify'; Body = @{ email = $c3.Email; code = $wrong } } })
    $attempts = Sql1 "SELECT attempts FROM auth_codes a JOIN users u ON u.id = a.user_id WHERE u.email = '$($c3.Email)' AND a.purpose = 'EMAIL_VERIFICATION' ORDER BY a.created_at DESC LIMIT 1;"
    Check 'CC-04' concurrent '30 parallel wrong codes: at most 4 answered INVALID_CODE' ((Count-Status $res 400 INVALID_CODE) -le 4) (Describe $res) 'API'
    Check 'CC-05' concurrent '30 parallel wrong codes: at most 5 attempts counted in the DB' ([int]$attempts -le 5) "attempts=$attempts"
    $r = Api POST /auth/email-verification/verify @{ email = $c3.Email; code = $right }
    Expect 'CC-06' concurrent 'right code after the burst is burned' $r 400 INVALID_OR_EXPIRED_CODE

    $c3b = New-Registered 'c3b'; $right = Get-DevCode 'Verification' $c3b.Email
    $wrong = if ($right -eq '000000') { '111111' } else { '000000' }
    $reqs = @(1..19 | ForEach-Object { @{ Method = 'POST'; Path = '/auth/email-verification/verify'; Body = @{ email = $c3b.Email; code = $wrong } } }) + @(@{ Method = 'POST'; Path = '/auth/email-verification/verify'; Body = @{ email = $c3b.Email; code = $right } })
    $res = Invoke-Parallel $reqs
    $attempts = Sql1 "SELECT attempts FROM auth_codes a JOIN users u ON u.id = a.user_id WHERE u.email = '$($c3b.Email)' AND a.purpose = 'EMAIL_VERIFICATION' ORDER BY a.created_at DESC LIMIT 1;"
    $accepted = (Count-Status $res 200) -eq 1
    Check 'CC-07' concurrent '19 wrong + 1 right in parallel: right code not accepted after 5+ wrong guesses' (-not ($accepted -and [int]$attempts -ge 5)) "accepted=$accepted, wrong attempts counted=$attempts; $(Describe $res)" 'API+DB'

    $c5 = New-Registered 'c5'
    $res = Invoke-Parallel (1..10 | ForEach-Object { @{ Method = 'POST'; Path = '/auth/password/forgot'; Body = @{ email = $c5.Email } } })
    $active = Sql1 "SELECT count(*) FROM auth_codes a JOIN users u ON u.id = a.user_id WHERE u.email = '$($c5.Email)' AND a.purpose = 'PASSWORD_RESET' AND a.consumed_at IS NULL;"
    Check 'CC-08' concurrent '10 parallel forgot -> exactly one 202' ((Count-Status $res 202) -eq 1) (Describe $res) 'API'
    Check 'CC-09' concurrent '...and exactly one active reset code in the DB' ($active -eq '1') "active codes=$active"

    $c6 = New-Verified 'c6'
    $res = Invoke-Parallel (@(1..5 | ForEach-Object { @{ Method = 'POST'; Path = '/auth/logout'; Token = $c6.Access } }) + @(1..3 | ForEach-Object { @{ Method = 'POST'; Path = '/auth/token/refresh'; Body = @{ refreshToken = $c6.Refresh } } }))
    $after = Api GET /users/me $null $c6.Access
    Check 'CC-10' concurrent '5 parallel logouts + 3 refreshes: no 5xx, token dead afterwards' (@($res | Where-Object { $_.Status -ge 500 }).Count -eq 0 -and $after.Status -eq 401) (Describe $res) 'API'
    $l = Api POST /auth/login @{ email = $c6.Email; password = $PW }
    Check 'CC-11' concurrent 'session_version in DB equals the claim of a fresh login' ((Get-DbUser $c6.Email).Version -eq (Get-ClaimVersion $l.Json.accessToken)) '' 'DB+Firebase'

    $m = $script:Main
    $res = Invoke-Parallel (1..20 | ForEach-Object { @{ Method = 'POST'; Path = '/auth/login'; Body = @{ email = $m.Email; password = $PW } } })
    Check 'CC-12' concurrent '20 parallel logins of one user -> all 200' ((Count-Status $res 200) -eq 20) (Describe $res) 'API'

    Wait-Cooldown $c4
    $res = Invoke-Parallel (1..10 | ForEach-Object { @{ Method = 'POST'; Path = '/auth/email-verification/resend'; Body = @{ email = $c4.Email } } })
    $active = Sql1 "SELECT count(*) FROM auth_codes a JOIN users u ON u.id = a.user_id WHERE u.email = '$($c4.Email)' AND a.purpose = 'EMAIL_VERIFICATION' AND a.consumed_at IS NULL;"
    Check 'CC-13' concurrent '10 parallel resends after the cooldown -> exactly one 202' ((Count-Status $res 202) -eq 1) (Describe $res) 'API'
    Check 'CC-14' concurrent '...and exactly one active verification code in the DB' ($active -eq '1') "active codes=$active"
}

function Phase7 {
    $prefix = "hq$TAG"
    $mismatch = @(); $checked = 0
    foreach ($e in @($Users.Keys)) {
        $db = Get-DbUser $e
        if (-not $db) { continue }                    # Firebase-only test user (TK-14)
        $s = $null; foreach ($p in $Users[$e]) { $s = Fb-SignIn $e $p; if ($s.Status -eq 200) { break } }
        $checked++
        if ($s.Status -ne 200) { $mismatch += "$e no Firebase login"; continue }
        if ($s.Json.localId -ne $db.Uid) { $mismatch += "$e uid differs" }
        $fv = (Fb-Lookup $s.Json.idToken).Json.users[0].emailVerified
        if ([bool]$fv -ne $db.Verified) { $mismatch += "$e emailVerified db=$($db.Verified) firebase=$fv" }
        if ((Get-ClaimVersion $s.Json.idToken) -ne $db.Version) { $mismatch += "$e session_version db=$($db.Version) claim=$(Get-ClaimVersion $s.Json.idToken)" }
    }
    Check 'DB-01' integrity "every test user: DB row matches Firebase (uid, emailVerified, session_version) - $checked users" ($mismatch.Count -eq 0 -and $checked -gt 0) ($mismatch -join '; ') 'DB+Firebase'

    $dbOnly = @(Sql "SELECT encode(convert_to(email, 'UTF8'), 'hex') FROM users WHERE email LIKE '$prefix%';" | ForEach-Object { FromHex $_.Trim() } | Where-Object { -not $Users.Contains($_) })
    Check 'DB-02' integrity 'no untracked DB rows (every row came from a successful sign-up)' ($dbOnly.Count -eq 0) ($dbOnly -join ', ')

    $badHash = Sql1 "SELECT count(*) FROM auth_codes a JOIN users u ON u.id = a.user_id WHERE u.email LIKE '$prefix%' AND a.code_hash !~ '^[0-9a-f]{64}$';"
    $total = Sql1 "SELECT count(*) FROM auth_codes a JOIN users u ON u.id = a.user_id WHERE u.email LIKE '$prefix%';"
    Check 'DB-03' integrity "all $total stored codes/tokens are 64-hex HMACs" ($badHash -eq '0' -and [int]$total -gt 0) "bad=$badHash"

    $dump = (Sql "SELECT row_to_json(u)::text FROM users u WHERE email LIKE '$prefix%' UNION ALL SELECT row_to_json(a)::text FROM auth_codes a JOIN users u ON u.id = a.user_id WHERE u.email LIKE '$prefix%';") -join "`n"
    # 6-digit codes are left out: digit runs occur naturally in UUIDs and timestamps. DB-03 covers codes.
    $plain = @($Secrets | Where-Object { $_.Length -ge 8 -and $_ -notmatch '^\d+$' })
    $found = @($plain | Where-Object { $dump.Contains($_) })
    Check 'DB-04' integrity "none of $($plain.Count) passwords/reset tokens appear in any DB row" ($found.Count -eq 0) "$($found.Count) found"

    Check 'DB-05' integrity 'database time zone is UTC' ((Sql1 'SHOW timezone;') -eq 'UTC')
    $m = $script:Main
    $apiCreated = (Api GET /users/me $null (Api POST /auth/login @{ email = $m.Email; password = $PW }).Json.accessToken).Json.createdAt
    $dbCreated = Sql1 "SELECT to_char(created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD""T""HH24:MI:SS') FROM users WHERE email = '$($m.Email)';"
    Check 'DB-06' integrity 'createdAt from the API equals the DB value (UTC)' (([DateTimeOffset]::Parse($apiCreated).UtcDateTime.ToString('yyyy-MM-ddTHH:mm:ss')) -eq $dbCreated) "api=$apiCreated db=$dbCreated"

    function Constraint([string]$Id, [string]$Case, [string]$Statement, [string]$Name) {
        $out = (Sql "BEGIN; $Statement ROLLBACK;") -join ' '
        Check $Id integrity $Case ($out -match $Name) ($out.Substring(0, [Math]::Min(110, $out.Length)))
    }
    Constraint 'DB-07' 'locale must be en or ar-EG' "INSERT INTO users (id, firebase_uid, email, phone, full_name, base_currency, locale, timezone, fcm_token, email_verified_at, terms_accepted_at, created_at, updated_at) VALUES (gen_random_uuid(), 'uid-$TAG-l', 'hq${TAG}l@x.example.com', NULL, 'X', 'EGP', 'fr', 'Africa/Cairo', NULL, NULL, now(), now(), now());" 'ck_users_locale'
    Constraint 'DB-08' 'email is unique' "INSERT INTO users (id, firebase_uid, email, full_name, terms_accepted_at, created_at, updated_at) VALUES (gen_random_uuid(), 'uid-$TAG-e', '$($m.Email)', 'X', now(), now(), now());" 'uk_users_email'
    $uid = (Get-DbUser $m.Email).Uid
    Constraint 'DB-09' 'firebase_uid is unique' "INSERT INTO users (id, firebase_uid, email, full_name, terms_accepted_at, created_at, updated_at) VALUES (gen_random_uuid(), '$uid', 'hq${TAG}u@x.example.com', 'X', now(), now(), now());" 'uk_users_firebase_uid'
    Constraint 'DB-10' 'auth_codes.purpose is restricted' "INSERT INTO auth_codes (id, user_id, purpose, code_hash, expires_at, created_at) SELECT gen_random_uuid(), id, 'ADMIN', 'x', now(), now() FROM users WHERE email = '$($m.Email)';" 'ck_auth_codes_purpose'
    $cascade = Sql "BEGIN; DELETE FROM users WHERE email = '$($m.Email)'; SELECT count(*) FROM auth_codes a WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.id = a.user_id); ROLLBACK;"
    Check 'DB-11' integrity 'deleting a user deletes its auth_codes (cascade)' (($cascade | Select-Object -Last 1).Trim() -eq '0') "orphans=$($cascade -join ',')"
    Check 'DB-12' integrity 'Firebase uid is never returned by the API' (-not ((Api GET /users/me $null (Api POST /auth/login @{ email = $m.Email; password = $PW }).Json.accessToken).Raw.Contains($uid))) '' 'API'
}

function Phase9 {
    $m = $script:Main
    $tok = (Api POST /auth/login @{ email = $m.Email; password = $PW }).Json.accessToken
    $times = @(); $fails = 0
    for ($i = 0; $i -lt 100; $i++) { $r = Api GET /users/me $null $tok; $times += $r.Ms; if ($r.Status -ne 200) { $fails++ } }
    $sorted = $times | Sort-Object; $p50 = $sorted[49]; $p95 = $sorted[94]
    Check 'LD-01' load '100 sequential GET /users/me all 200, p95 under 1 s' ($fails -eq 0 -and $p95 -lt 1000) "p50=$p50 ms, p95=$p95 ms, max=$($sorted[99]) ms" 'API'
    $res = Invoke-Parallel (1..20 | ForEach-Object { @{ Method = 'GET'; Path = '/users/me'; Token = $tok } })
    $ms = ($res | ForEach-Object { $_.Ms } | Measure-Object -Maximum).Maximum
    Check 'LD-02' load '20 concurrent GET /users/me all 200' ((Count-Status $res 200) -eq 20) "$(Describe $res); slowest $ms ms" 'API'
}

function Wait-Health([string]$Want, [int]$Seconds) {
    $deadline = (Get-Date).AddSeconds($Seconds)
    do { $h = Send-Http GET "$BASE/actuator/health" -TimeoutMs 45000; if ($h.Json.status -eq $Want) { return $h }; Start-Sleep -Seconds 2 } while ((Get-Date) -lt $deadline)
    $h
}

function Phase8 {
    if ($SkipOutage) { Info 'OUT-00' resilience 'DB outage phase skipped' 'skipped' '-SkipOutage'; return }
    $m = $script:Main
    $tok = (Api POST /auth/login @{ email = $m.Email; password = $PW }).Json.accessToken
    $before = Sql1 "SELECT count(*) FROM users WHERE email LIKE 'hq$TAG%';"
    $outEmail = New-Email 'ob'
    try {
        docker compose stop db 2>&1 | Out-Null
        $h = Wait-Health 'DOWN' 60
        Expect 'OUT-01' resilience 'health reports DOWN when the DB is stopped' $h 503 '' ($h.Json.status -eq 'DOWN')
        $r = Api GET /users/me $null $tok
        Expect 'OUT-02' resilience 'GET /users/me during the outage: clean JSON 5xx' $r 500, 503 '' ([bool]$r.Code) "took $($r.Ms) ms; body: $("$($r.Raw)".Substring(0, [Math]::Min(100, "$($r.Raw)".Length)))"
        $r = Api POST /auth/register @{ fullName = 'Outage Tester'; email = $outEmail; password = $PW; acceptedTerms = $true }
        Expect 'OUT-03' resilience 'register during the outage: clean JSON 5xx' $r 500, 503 '' ([bool]$r.Code) "took $($r.Ms) ms"
        $r = Api POST /auth/login @{ email = $m.Email; password = $PW }
        Expect 'OUT-04' resilience 'login during the outage: clean JSON 5xx' $r 500, 503 '' ([bool]$r.Code) "took $($r.Ms) ms"
    } finally {
        docker compose start db 2>&1 | Out-Null
    }
    $h = Wait-Health 'UP' 120
    Expect 'OUT-05' resilience 'health back to UP after the DB restarts' $h 200 '' ($h.Json.status -eq 'UP')
    $r = Api POST /auth/login @{ email = $m.Email; password = $PW };  Expect 'OUT-06' resilience 'login works again' $r 200
    $r = Api POST /auth/register @{ fullName = 'Outage Tester'; email = $outEmail; password = $PW; acceptedTerms = $true }
    Expect 'OUT-07' resilience 'the sign-up that failed left no Firebase orphan (same email registers now)' $r 201 '' $true '' 'API+Firebase'

    docker compose restart backend 2>&1 | Out-Null
    $h = Wait-Health 'UP' 120
    $r = Api POST /auth/login @{ email = $m.Email; password = $PW };  Expect 'OUT-08' resilience 'backend restart: login works' $r 200
    $after = Sql1 "SELECT count(*) FROM users WHERE email LIKE 'hq$TAG%';"
    Check 'OUT-09' resilience 'backend restart: no data lost' ([int]$after -eq [int]$before + 1) "before=$before after=$after"
}

function Cleanup {
    $script:CurrentPhase = 'Cleanup'
    Write-Host "`n== Cleanup" -ForegroundColor Cyan
    $deleted = 0; $failed = @()
    foreach ($e in @($Users.Keys)) {
        $done = $false
        $list = @($Users[$e]); [array]::Reverse($list)      # newest password first
        foreach ($p in $list) {
            # Loop: a sign-up race can leave several Firebase accounts behind one email (see CC-01 / DB-01).
            for ($n = 0; $n -lt 10; $n++) {
                $s = Fb-SignIn $e $p
                if ($s.Status -ne 200) { break }
                $d = Fb delete @{ idToken = $s.Json.idToken }; if ($d.Status -eq 200) { $deleted++; $done = $true } else { break }
            }
        }
        if (-not $done) { $failed += $e }
    }
    Sql "DELETE FROM users WHERE email LIKE 'hq$TAG%';" | Out-Null
    $left = Sql1 "SELECT count(*) FROM users WHERE email LIKE 'hq$TAG%';"
    Check 'CLN-01' cleanup "Firebase test accounts deleted: $deleted (for $($Users.Count) tracked emails)" ($failed.Count -eq 0) ($failed -join ', ') 'Firebase'
    Check 'CLN-02' cleanup 'no hq<tag> rows left in the DB' ($left -eq '0') "left=$left"
}

# ===============================================================================================================
# Main
# ===============================================================================================================
$names = @{ 0 = 'Phase 0 - Preflight'; 1 = 'Phase 1 - Input validation'; 2 = 'Phase 2 - Password policy (weak data)';
    3 = 'Phase 3 - Business flows and state'; 4 = 'Phase 4 - Tokens and access control'; 5 = 'Phase 5 - Abuse and security';
    6 = 'Phase 6 - Concurrency and races'; 7 = 'Phase 7 - DB and Firebase integrity'; 8 = 'Phase 8 - Resilience (DB outage)';
    9 = 'Phase 9 - Light load' }
Write-Host "Masroofy hard test - run tag $TAG - $BASE" -ForegroundColor Cyan
$started = Get-Date
try {
    $script:CurrentPhase = 'Setup'
    $script:Main = New-Verified 'main'
    foreach ($n in $PhaseList) {
        $script:CurrentPhase = $names[$n]
        Write-Host "`n== $($names[$n])" -ForegroundColor Cyan
        try { & "Phase$n" } catch { Add-Result "P$n-ERR" error 'phase aborted by an exception' 'phase completes' "$($_.Exception.Message)" FAIL "$($_.InvocationInfo.ScriptLineNumber)" 'Runner' }
    }
} catch {
    Add-Result 'SETUP' error 'setup failed' 'ok' "$($_.Exception.Message)" FAIL '' 'Runner'
} finally {
    try { Cleanup } catch { Add-Result 'CLN-ERR' error 'cleanup failed' 'ok' "$($_.Exception.Message)" FAIL '' 'Runner' }
}

$outDir = Join-Path (Get-Location) 'target\hard-test'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$Results | ConvertTo-Json -Depth 4 | Out-File (Join-Path $outDir 'results.json') -Encoding utf8
$md = New-Object System.Text.StringBuilder
[void]$md.AppendLine("# Hard test results (run tag $TAG, $($started.ToString('yyyy-MM-dd HH:mm')), $([int]((Get-Date) - $started).TotalSeconds) s)`n")
[void]$md.AppendLine('| Phase | Pass | Fail | Info |'); [void]$md.AppendLine('|---|---|---|---|')
foreach ($g in ($Results | Group-Object Phase)) {
    [void]$md.AppendLine("| $($g.Name) | $(@($g.Group | Where-Object Result -eq PASS).Count) | $(@($g.Group | Where-Object Result -eq FAIL).Count) | $(@($g.Group | Where-Object Result -eq INFO).Count) |")
}
foreach ($g in ($Results | Group-Object Phase)) {
    [void]$md.AppendLine("`n## $($g.Name)`n"); [void]$md.AppendLine('| ID | Result | Class | Layer | Case | Expected | Actual | Note |'); [void]$md.AppendLine('|---|---|---|---|---|---|---|---|')
    foreach ($x in $g.Group) { [void]$md.AppendLine("| $($x.Id) | $($x.Result) | $($x.Class) | $($x.Layer) | $($x.Case.Replace('|', '\|')) | $($x.Expected) | $($x.Actual) | $($x.Note.Replace('|', '\|')) |") }
}
$md.ToString() | Out-File (Join-Path $outDir 'results.md') -Encoding utf8

$pass = @($Results | Where-Object Result -eq PASS).Count; $fail = @($Results | Where-Object Result -eq FAIL).Count; $info = @($Results | Where-Object Result -eq INFO).Count
Write-Host "`nTOTAL: $pass passed, $fail failed, $info observations  (run tag $TAG, $([int]((Get-Date) - $started).TotalSeconds) s)" -ForegroundColor $(if ($fail) { 'Red' } else { 'Green' })
Write-Host "Results: $outDir\results.md"
