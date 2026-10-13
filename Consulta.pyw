import csv
import io
import tkinter as tk
from tkinter import messagebox
from urllib.parse import urlparse, parse_qs

import requests


# Link da planilha fornecido
LINK_PLANILHA = (
    "https://docs.google.com/spreadsheets/d/"
    "13bnnwDdEty5VoVOMDRDXm5U8GoKaNJo6IjJoBiZVTVw/"
    "edit?gid=0#gid=0"
)


def criar_link_csv(link_planilha):
    """Converte o link de edição do Google Sheets em um link de exportação CSV."""
    partes = urlparse(link_planilha)
    segmentos = partes.path.strip("/").split("/")

    try:
        indice = segmentos.index("d")
        id_planilha = segmentos[indice + 1]
    except (ValueError, IndexError):
        raise ValueError("Não foi possível identificar o ID da planilha no link.")

    parametros = parse_qs(partes.query)
    gid = parametros.get("gid", [None])[0]

    # Alguns links têm o gid após #gid= em vez de na query.
    if not gid and partes.fragment.startswith("gid="):
        gid = partes.fragment.split("=", 1)[1]

    if not gid:
        gid = "0"

    return (
        f"https://docs.google.com/spreadsheets/d/{id_planilha}"
        f"/export?format=csv&gid={gid}"
    )


def carregar_dados_da_planilha():
    """Baixa a aba como CSV e retorna suas linhas."""
    url_csv = criar_link_csv(LINK_PLANILHA)

    resposta = requests.get(
        url_csv,
        timeout=30,
        headers={"User-Agent": "Mozilla/5.0"}
    )
    resposta.raise_for_status()

    # utf-8-sig também trata arquivos CSV com BOM.
    conteudo = resposta.content.decode("utf-8-sig")
    leitor = csv.reader(io.StringIO(conteudo))
    linhas = list(leitor)

    if not linhas:
        raise ValueError("A planilha está vazia.")

    return linhas


class BuscadorScripts:
    def __init__(self, janela):
        self.janela = janela
        self.janela.title("Buscador de Scripts")
        self.janela.geometry("750x520")
        self.janela.minsize(550, 400)

        tk.Label(
            janela,
            text="Buscador de scripts por assunto",
            font=("Arial", 16, "bold")
        ).pack(pady=(15, 8))

        tk.Label(
            janela,
            text="A busca consulta a planilha online ao clicar em Buscar."
        ).pack(pady=(0, 10))

        tk.Label(janela, text="Assunto:").pack()

        linha_busca = tk.Frame(janela)
        linha_busca.pack(pady=8)

        self.campo_busca = tk.Entry(linha_busca, width=45)
        self.campo_busca.pack(side=tk.LEFT, padx=5)
        self.campo_busca.bind("<Return>", lambda evento: self.buscar())

        self.botao_buscar = tk.Button(
            linha_busca,
            text="Buscar",
            command=self.buscar
        )
        self.botao_buscar.pack(side=tk.LEFT, padx=5)

        self.status = tk.Label(janela, text="Pronto")
        self.status.pack(pady=3)

        self.resultados = tk.Text(
            janela,
            wrap=tk.WORD,
            font=("Arial", 10)
        )
        self.resultados.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

    def buscar(self):
        assunto_buscado = self.campo_busca.get().strip().casefold()

        if not assunto_buscado:
            messagebox.showwarning("Atenção", "Digite um assunto para buscar.")
            return

        self.botao_buscar.config(state=tk.DISABLED)
        self.status.config(text="Consultando a planilha...")
        self.resultados.delete("1.0", tk.END)
        self.janela.update_idletasks()

        try:
            linhas = carregar_dados_da_planilha()

            cabecalhos = [valor.strip().casefold() for valor in linhas[0]]

            if "assunto" not in cabecalhos or "script" not in cabecalhos:
                raise ValueError(
                    "A primeira linha da planilha deve conter as colunas "
                    "'Assunto' e 'Script'."
                )

            indice_assunto = cabecalhos.index("assunto")
            indice_script = cabecalhos.index("script")

            encontrados = []

            for linha in linhas[1:]:
                if max(indice_assunto, indice_script) >= len(linha):
                    continue

                assunto = linha[indice_assunto].strip()
                script = linha[indice_script].strip()

                if assunto_buscado in assunto.casefold():
                    encontrados.append((assunto, script))

            if encontrados:
                for numero, (assunto, script) in enumerate(encontrados, start=1):
                    self.resultados.insert(
                        tk.END,
                        f"Resultado {numero}\n"
                        f"Assunto: {assunto}\n"
                        f"Script:\n{script}\n\n"
                        f"{'-' * 60}\n\n"
                    )

                self.status.config(
                    text=f"{len(encontrados)} resultado(s) encontrado(s)."
                )
            else:
                self.resultados.insert(
                    tk.END,
                    "Nenhum script encontrado para esse assunto."
                )
                self.status.config(text="Busca concluída.")

        except requests.exceptions.Timeout:
            messagebox.showerror(
                "Tempo esgotado",
                "A planilha demorou muito para responder. Tente novamente."
            )
            self.status.config(text="Falha na conexão.")

        except requests.exceptions.RequestException as erro:
            messagebox.showerror(
                "Erro ao acessar a planilha",
                "Não foi possível baixar os dados. Verifique sua conexão "
                "e se a planilha está compartilhada para leitura.\n\n"
                f"Detalhes: {erro}"
            )
            self.status.config(text="Falha ao acessar a planilha.")

        except Exception as erro:
            messagebox.showerror("Erro", str(erro))
            self.status.config(text="Erro na busca.")

        finally:
            self.botao_buscar.config(state=tk.NORMAL)


if __name__ == "__main__":
    janela = tk.Tk()
    app = BuscadorScripts(janela)
    janela.mainloop()
