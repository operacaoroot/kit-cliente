# ============================================================================
#  pedir-segredo.ps1 - janela do Windows para a pessoa digitar um segredo (senha,
#  token). Chamado por ferramentas\sistemas.py --gravar-credencial; nao rode direto.
#  ASCII puro de proposito: o texto com acento chega pelas variaveis KIT_TITULO e
#  KIT_ROTULO. Devolve o segredo em base64 na saida padrao, para o Python gravar no
#  arquivo do plugin sem mostrar na tela. Sai com 1 se a pessoa cancelar.
# ============================================================================
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()

$titulo = $env:KIT_TITULO
if (-not $titulo) { $titulo = "Kit" }
$rotulo = $env:KIT_ROTULO
if (-not $rotulo) { $rotulo = "Digite o segredo" }

$form = New-Object System.Windows.Forms.Form
$form.Text = $titulo
$form.StartPosition = "CenterScreen"
$form.TopMost = $true
$form.FormBorderStyle = "FixedDialog"
$form.MaximizeBox = $false
$form.MinimizeBox = $false
$form.ClientSize = New-Object System.Drawing.Size(440, 160)
$form.Font = New-Object System.Drawing.Font("Segoe UI", 10)

$texto = New-Object System.Windows.Forms.Label
$texto.Text = $rotulo
$texto.AutoSize = $false
$texto.SetBounds(16, 12, 408, 44)

$caixa = New-Object System.Windows.Forms.TextBox
$caixa.UseSystemPasswordChar = $true
$caixa.SetBounds(16, 62, 408, 28)

$ok = New-Object System.Windows.Forms.Button
$ok.Text = "Gravar"
$ok.SetBounds(240, 112, 88, 32)
$ok.DialogResult = [System.Windows.Forms.DialogResult]::OK

$cancelar = New-Object System.Windows.Forms.Button
$cancelar.Text = "Cancelar"
$cancelar.SetBounds(336, 112, 88, 32)
$cancelar.DialogResult = [System.Windows.Forms.DialogResult]::Cancel

$form.Controls.AddRange(@($texto, $caixa, $ok, $cancelar))
$form.AcceptButton = $ok
$form.CancelButton = $cancelar
$form.Add_Shown({ $form.Activate(); $caixa.Focus() })

$resultado = $form.ShowDialog()
if ($resultado -ne [System.Windows.Forms.DialogResult]::OK -or -not $caixa.Text) { exit 1 }
[Console]::Out.Write([Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($caixa.Text)))
exit 0
