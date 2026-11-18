# fix6 FINAL - Bloco 3 sem Data inicial
# Dias da semana + Horario de/ate + Duracao
import re, glob

# Acha o arquivo certo
html_path = "templates/admin_calendar.html"
print(f"Arquivo: {html_path}")

with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
    html = f.read()

# 1. TIRA Data inicial do Bloco 3 - só se tiver
# Não apaga os do Bloco 1 e 2, só o que está perto de "Dias da semana"
if "Dias da semana" in html:
    # Pega a parte antes e depois para não apagar bloco 1 e 2
    partes = html.split("Dias da semana")
    # Só mexe na parte ANTES de Dias da semana, nos últimos 500 caracteres
    antes = partes[0]
    # Remove input type=date que está logo antes de Dias da semana
    antes = re.sub(r'Data inicial:.*?<input[^>]*type="date"[^>]*>.*?<br>', '<!-- Data inicial removida fix6 --><br>', antes, flags=re.DOTALL|re.IGNORECASE)
    # Se não achou desse jeito, tenta só remover o label
    antes = re.sub(r'Data inicial:.*?<br>', '', antes, flags=re.IGNORECASE, count=1)
    html = antes + "Dias da semana" + "Dias da semana".join(partes[1:])
    print("Data inicial do Bloco 3 removida!")

# 2. Troca texto de ajuda
html = html.replace(
    "Escolha a data inicial",
    "Marque os dias da semana, o horario de / ate, e por quanto tempo"
)

# 3. Se ainda não tem Horario + Duracao, adiciona
if "Por quanto tempo" not in html:
    novo = """
    <div style="margin:15px 0;">
      <b>Horario:</b><br>
      De: <input type="time" name="hora_inicio" value="10:00">
      Ate: <input type="time" name="hora_fim" value="12:00">
    </div>
    <div style="margin:15px 0;">
      <b>Bloquear por quanto tempo?</b><br>
      <label style="display:block; margin:6px 0;"><input type="radio" name="duracao_bloco3" value="essa_semana" checked> So essa semana</label>
      <label style="display:block; margin:6px 0;"><input type="radio" name="duracao_bloco3" value="mes_todo"> O mes todo</label>
      <label style="display:block; margin:6px 0;"><input type="radio" name="duracao_bloco3" value="sempre"> Sempre</label>
    </div>
    """
    # Acha o botao Bloquear do Bloco 3 (o que vem depois de Dias da semana)
    idx = html.find("Dias da semana")
    idx_botao = html.find("Bloquear", idx)
    if idx_botao != -1:
        # Volta até o <button
        idx_button_start = html.rfind("<button", 0, idx_botao)
        html = html[:idx_button_start] + novo + html[idx_button_start:]
        print("Horario + Duracao adicionados!")

with open(html_path, "w", encoding="utf-8") as f:
    f.write(html)

print("PRONTO fix6! Recarrega a pagina.")