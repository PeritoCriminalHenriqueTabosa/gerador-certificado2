# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, flash, redirect, url_for, send_file
import datetime
import pytz
from fpdf import FPDF
import io
import os
import traceback

# Cria a instância da aplicação Flask
app = Flask(__name__)

# --- Configuração Geral ---
app.secret_key = 'coloque_uma_chave_secreta_aqui_12345' # !! MUDE ISSO !!
PALAVRA_CHAVE_CORRETA = "MORTE" # !! SUBSTITUA !!
INICIO_PERMITIDO_STR = "2025-07-24 00:00:00" # !! AJUSTE !!
FIM_PERMITIDO_STR = "2025-08-29 23:59:59" # !! AJUSTE !!
TIMEZONE_STR = 'America/Recife' # !! AJUSTE SE NECESSÁRIO !!

try:
    TIMEZONE = pytz.timezone(TIMEZONE_STR)
except pytz.exceptions.UnknownTimeZoneError:
    print(f"ERRO: Fuso horário '{TIMEZONE_STR}' desconhecido. Usando UTC como padrão.")
    TIMEZONE = pytz.utc

# --- Configurações do PDF ---
TEMPLATE_IMAGE_PATH = "certificado30032025aula11.png" # !! VERIFIQUE NOME E LOCAL !!

# --- ALTERADO: Orientação para Paisagem ('L') ---
PDF_ORIENTATION = 'L' # 'P' = Retrato, 'L' = Landscape (Paisagem)
PDF_WIDTH = 297 if PDF_ORIENTATION == 'L' else 210 # Largura A4 Paisagem = 297mm
PDF_HEIGHT = 210 if PDF_ORIENTATION == 'L' else 297 # Altura A4 Paisagem = 210mm

# --- ALTERADO: Fontes ---
# !! IMPORTANTE: Baixe Montserrat-ExtraBold.ttf e coloque na pasta 'fonts' !!
# O nome 'MontserratEB' é um alias que definimos em pdf.add_font()
FONTE_NOME = 'MontserratEB' 
FONTE_NOME_ARQUIVO = 'fonts/Montserrat-ExtraBold.ttf' # Caminho para o arquivo .ttf
FONTE_CPF = 'Arial' # Arial é padrão, não precisa adicionar arquivo

# --- ALTERADO: Coordenadas e Largura (AJUSTE PARA PAISAGEM!) ---
# !! VOCÊ PRECISARÁ AJUSTAR ESTES VALORES PARA O LAYOUT PAISAGEM !!
NOME_X_CENTRO = PDF_WIDTH / 2  # Centro horizontal (148.5mm) - AJUSTE FINO
NOME_Y = 89                    # Posição vertical - AJUSTE
NOME_LARGURA_MAX = 220         # Largura máxima para o nome - AJUSTE
NOME_FONTE_MAX_SIZE = 30
NOME_FONTE_MIN_SIZE = 10

CPF_X_CENTRO = PDF_WIDTH / 2   # Centro horizontal - AJUSTE FINO
CPF_Y = 98                     # Posição vertical - AJUSTE
CPF_FONTE_SIZE = 20

# --- Função para Gerar o PDF (Revisada) ---
def gerar_certificado_pdf(nome, cpf):
    """
    Gera o PDF do certificado com base no template e nos dados do usuário.
    Retorna um objeto BytesIO com o PDF ou None em caso de erro.
    """
    try:
        template_path_abs = os.path.abspath(TEMPLATE_IMAGE_PATH)
        if not os.path.exists(template_path_abs):
             raise FileNotFoundError(f"Arquivo de template não encontrado em: {template_path_abs}")

        # Cria o objeto PDF (orientação, unidade, formato) - Usando PDF_ORIENTATION
        pdf = FPDF(orientation=PDF_ORIENTATION, unit='mm', format='A4')
        pdf.add_page()
        pdf.set_auto_page_break(auto=False, margin=0)

        # --- ALTERADO: Adiciona a fonte Montserrat ---
        # Verifica se o arquivo da fonte existe antes de adicioná-lo
        fonte_nome_path_abs = os.path.abspath(FONTE_NOME_ARQUIVO)
        if not os.path.exists(fonte_nome_path_abs):
            raise FileNotFoundError(f"Arquivo de fonte '{FONTE_NOME_ARQUIVO}' não encontrado em: {fonte_nome_path_abs}")
        
        # Adiciona a fonte TTF ao FPDF. 'uni=True' para suporte a UTF-8.
        pdf.add_font(FONTE_NOME, 'B', fonte_nome_path_abs, uni=True) # 'B' para negrito (se o arquivo for ExtraBold, pode usar '')

        # Adiciona a imagem de fundo
        pdf.image(template_path_abs, x=0, y=0, w=PDF_WIDTH, h=PDF_HEIGHT)

        # --- Processamento do Nome ---
        pdf.set_font(FONTE_NOME, 'B', NOME_FONTE_MAX_SIZE) # Usa a fonte Montserrat adicionada
        tamanho_fonte_nome_atual = NOME_FONTE_MAX_SIZE
        
        # FPDF com fontes TTF unicode espera strings normais (não precisa de encode/decode manual)
        largura_nome = pdf.get_string_width(nome) 

        # Reduz o tamanho da fonte se o nome for muito longo
        while largura_nome > NOME_LARGURA_MAX and tamanho_fonte_nome_atual > NOME_FONTE_MIN_SIZE:
            tamanho_fonte_nome_atual -= 1
            pdf.set_font_size(tamanho_fonte_nome_atual)
            largura_nome = pdf.get_string_width(nome)

        nome_x = NOME_X_CENTRO - (largura_nome / 2)
        pdf.set_xy(nome_x, NOME_Y)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(w=largura_nome, h=10, txt=nome, border=0, ln=0, align='C')

        # --- Processamento do CPF ---
        cpf_formatado = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
        # --- ALTERADO: Usa Arial Bold ('B') ---
        pdf.set_font(FONTE_CPF, 'B', CPF_FONTE_SIZE) # 'B' para negrito

        largura_cpf = pdf.get_string_width(cpf_formatado)
        cpf_x = CPF_X_CENTRO - (largura_cpf / 2)
        pdf.set_xy(cpf_x, CPF_Y)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(w=largura_cpf, h=10, txt=cpf_formatado, border=0, ln=0, align='C')

        # --- Saída do PDF ---
        # Usar pdf.output() sem encoding manual quando uni=True é usado na fonte
        pdf_buffer = io.BytesIO(pdf.output())
        
        print("Buffer PDF criado com sucesso.")
        return pdf_buffer

    except FileNotFoundError as e:
        print(f"ERRO ao gerar PDF (Arquivo): {e}")
        flash(f"Erro interno: {e}. Verifique as configurações.", "error")
        return None
    except RuntimeError as e: # Captura erros específicos do FPDF (ex: fonte não encontrada)
        print(f"ERRO FPDF ao gerar PDF: {e}")
        traceback.print_exc()
        flash(f"Erro interno do FPDF ({e}). Verifique as fontes ou contate o administrador.", "error")
        return None
    except Exception as e:
        print(f"ERRO inesperado ao gerar PDF:")
        traceback.print_exc()
        flash(f"Erro interno ({type(e).__name__}) ao gerar o certificado. Contate o administrador.", "error")
        return None


# --- Rota Principal (Lógica de validação e chamada da geração de PDF permanece a mesma) ---
@app.route('/', methods=['GET', 'POST'])
def homepage():
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        cpf = request.form.get('cpf', '').strip()
        palavra_chave_digitada = request.form.get('palavra_chave', '').strip()

        if not nome or not cpf or not palavra_chave_digitada:
            flash("Todos os campos são obrigatórios.", "error")
            return redirect(url_for('homepage'))

        if not (cpf.isdigit() and len(cpf) == 11):
            flash("CPF inválido. Digite apenas os 11 números.", "error")
            return redirect(url_for('homepage'))

        try:
            inicio_permitido = TIMEZONE.localize(datetime.datetime.strptime(INICIO_PERMITIDO_STR, '%Y-%m-%d %H:%M:%S'))
            fim_permitido = TIMEZONE.localize(datetime.datetime.strptime(FIM_PERMITIDO_STR, '%Y-%m-%d %H:%M:%S'))
            agora = datetime.datetime.now(TIMEZONE)
        except ValueError:
             flash("Erro interno na configuração de datas. Contate o administrador.", "error")
             print("ERRO: Falha ao converter datas/horas da configuração.")
             return redirect(url_for('homepage'))
        except Exception as e:
             flash("Erro interno ao processar datas/horas. Contate o administrador.", "error")
             print(f"ERRO inesperado com datas/horas: {e}")
             return redirect(url_for('homepage'))

        if palavra_chave_digitada != PALAVRA_CHAVE_CORRETA:
            flash("Palavra-chave incorreta. Tente novamente.", "error")
            return redirect(url_for('homepage'))

        if not (inicio_permitido <= agora <= fim_permitido):
            inicio_fmt = inicio_permitido.strftime('%d/%m/%Y %H:%M')
            fim_fmt = fim_permitido.strftime('%d/%m/%Y %H:%M')
            flash(f"Emissão permitida apenas entre {inicio_fmt} e {fim_fmt} ({TIMEZONE_STR}).", "error")
            return redirect(url_for('homepage'))

        print(f"Validação OK: Nome='{nome}', CPF='{cpf}'. Tentando gerar PDF...")
        pdf_buffer = gerar_certificado_pdf(nome, cpf)

        if pdf_buffer:
            nome_sanitizado = "".join(c for c in nome if c.isalnum() or c in (' ', '_')).rstrip().replace(' ', '_')
            nome_sanitizado = nome_sanitizado[:50] 
            nome_arquivo = f"Certificado_{nome_sanitizado}.pdf"
            
            print(f"PDF gerado com sucesso. Enviando como '{nome_arquivo}'")
            
            return send_file(
                pdf_buffer,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=nome_arquivo
            )
        else:
            # Erro já foi 'flashed' dentro de gerar_certificado_pdf
            return redirect(url_for('homepage'))

    # Requisição GET
    return render_template('index.html')

# Bloco para rodar o servidor de desenvolvimento
if __name__ == '__main__':
    # Cria a pasta 'fonts' se ela não existir (apenas como conveniência)
    if not os.path.exists('fonts'):
        os.makedirs('fonts')
        print("Pasta 'fonts' criada. Coloque o arquivo Montserrat-ExtraBold.ttf nela.")

    print("-" * 40)
    print("Iniciando Gerador de Certificados...")
    print(f"Verifique se as bibliotecas Flask, fpdf2 e pytz estão instaladas:")
    print("  pip install Flask fpdf2 pytz")
    print(f"Certifique-se que o arquivo de template:")
    print(f"  '{os.path.abspath(TEMPLATE_IMAGE_PATH)}'")
    print(f"  existe e está acessível.")
    print(f"Certifique-se que o arquivo de fonte:")
    print(f"  '{os.path.abspath(FONTE_NOME_ARQUIVO)}'")
    print(f"  existe e está acessível.")
    print(f"Verifique e ajuste as CONFIGURAÇÕES no código app.py:")
    print(f"  - app.secret_key (mude para algo seguro)")
    print(f"  - PALAVRA_CHAVE_CORRETA")
    print(f"  - INICIO_PERMITIDO_STR e FIM_PERMITIDO_STR")
    print(f"  - TIMEZONE_STR")
    print(f"  - TEMPLATE_IMAGE_PATH")
    print(f"  - PDF_ORIENTATION (agora '{PDF_ORIENTATION}')")
    print(f"  - NOME_X_CENTRO, NOME_Y, NOME_LARGURA_MAX (AJUSTAR PARA PAISAGEM!)")
    print(f"  - CPF_X_CENTRO, CPF_Y (AJUSTAR PARA PAISAGEM!)")
    print(f"  - FONTE_NOME ('{FONTE_NOME}'), FONTE_CPF ('{FONTE_CPF}' Bold)")
    print("-" * 40)
    app.run(debug=True, host='0.0.0.0', port=5000)
