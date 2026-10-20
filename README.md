# 🤖 Robozinho Organizador de Arquivos & Mesclador Inteligente de PDFs

Automatize a rotina de descompactar arquivos ZIP, juntar guias/declarações em PDF e organizar pastas no Windows e Linux.

---

## 📥 Como baixar no computador (Para quem não entende de programação):

1. **Clique no link direto para baixar o ZIP:**
   👉 **[Clique aqui para Baixar o Robozinho](https://github.com/SENPedroVitor/robozinho-leo-pregui-a/archive/refs/heads/main.zip)**
2. Abra o arquivo ZIP baixado e extraia a pasta (por exemplo, na sua **Área de Trabalho** ou onde preferir).
3. Abra a pasta e dê **dois cliques** no arquivo:
   👉 **`executar_robozinho.bat`**

> **Importante:** Você só precisa ter o **[Python](https://www.python.org/downloads/)** instalado no computador. Ao instalar o Python, marque a caixinha **"Add python.exe to PATH"**. O robô faz todo o resto sozinho!

---

## ⚡ Como Usar

Ao abrir o robô com 2 cliques, ele mostra um menu simples na tela:

```text
============================================================
          🤖 ROBOZINHO DE ARQUIVOS & PDFS 🤖
============================================================
 [1] 📥 Organizar a pasta DOWNLOADS
 [2] 📁 Organizar ESTA PASTA do Robozinho
 [3] 📂 Escolher OUTRA pasta (digite ou arraste a pasta)
 [4] 📑 Apenas Extrair ZIPs e Juntar PDFs (fiscal/contábil)
 [0] ❌ Sair
============================================================
```

- **Opção 1 (Mais prática):** Ele varre direto sua pasta **Downloads**, descompacta os ZIPs que você acabou de baixar e junta os PDFs de cada cliente automaticamente!
- **Opção 2:** Organiza a pasta onde o robô está instalado.

---

## 🧠 Como Funciona o Agrupamento Inteligente de PDFs?

- **Identifica clientes pelo código:** junta documentos como `496 IRPJ.pdf`, `496 CSLL.pdf`, `496 PIS.pdf` em **`496_Completo.pdf`** na pasta `PDFs_Juntados`.
- **Suporta mais de 2 arquivos:** agrupa 2, 3, 4, 5 ou mais documentos do mesmo cliente sem misturar.
- **Ordem prioritária:** coloca na sequência correta (IRPJ ➔ CSLL ➔ PIS ➔ Guias/DARFs ➔ Recibos).
- **Segurança total:** seus arquivos originais nunca são apagados nem perdidos.
