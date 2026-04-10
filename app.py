from flask import Flask, render_template, request, redirect, session
import sqlite3
import requests
import matplotlib.pyplot as plt
import os

app = Flask(__name__)
app.secret_key = "chave_secreta_super_segura"

# ----------------------------
# BANCO DE DADOS
# ----------------------------
def conectar():
    conn = sqlite3.connect("dados.db")
    conn.row_factory = sqlite3.Row
    return conn


def criar_tabelas():
    conn = conectar()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE,
            senha TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS transacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT,
            nome TEXT,
            valor REAL,
            tipo TEXT
        )
    """)

    conn.commit()
    conn.close()

criar_tabelas()

def gerar_grafico(usuario):
    conn = conectar()
    c = conn.cursor()

    c.execute("""
        SELECT tipo, SUM(valor) as total
        FROM transacoes
        WHERE usuario=?
        GROUP BY tipo
    """, (usuario,))

    dados = c.fetchall()

    entradas = 0
    saidas = 0

    for d in dados:
        if d["tipo"] == "entrada":
            entradas = d["total"] or 0
        else:
            saidas = d["total"] or 0

    labels = ["Entradas", "Saídas"]
    valores = [entradas, saidas]

    plt.figure()
    plt.bar(labels, valores)

    if not os.path.exists("static"):
        os.makedirs("static")

    caminho = "static/grafico.png"
    plt.savefig(caminho)
    plt.close()

    return caminho

# ----------------------------
# DÓLAR (API ESTÁVEL)
# ----------------------------
def pegar_dolar():
    try:
        url = "https://api.exchangerate.host/latest?base=USD&symbols=BRL"
        data = requests.get(url).json()
        return round(data["rates"]["BRL"], 2)
    except:
        return "Indisponível"


# ----------------------------
# HOME
# ----------------------------
@app.route("/")
def home():
    if "usuario" not in session:
        return redirect("/login")

    conn = conectar()
    c = conn.cursor()

    c.execute("SELECT * FROM transacoes WHERE usuario=?",
              (session["usuario"],))
    transacoes = c.fetchall()

    saldo = 0
    total_saidas = 0
    total_entradas = 0

    for t in transacoes:
        if t["tipo"] == "entrada":
            saldo += t["valor"]
            total_entradas += t["valor"]
        else:
            saldo -= t["valor"]
            total_saidas += t["valor"]

    grafico = gerar_grafico(session["usuario"])
    dolar = pegar_dolar()

    # 🔥 INSIGHT SIMPLES (INTELIGÊNCIA)
    if total_saidas > total_entradas:
        alerta = "⚠ Você está gastando mais do que ganha!"
    else:
        alerta = "✅ Sua saúde financeira está ok."

    return render_template(
        "index.html",
        transacoes=transacoes,
        saldo=saldo,
        dolar=dolar,
        grafico=grafico,
        alerta=alerta
    )


# ----------------------------
# LOGIN
# ----------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        senha = request.form["senha"]

        conn = conectar()
        c = conn.cursor()

        c.execute("SELECT * FROM usuarios WHERE usuario=? AND senha=?",
                  (usuario, senha))

        user = c.fetchone()

        if user:
            session["usuario"] = usuario
            return redirect("/")
        else:
            return "Login inválido"

    return render_template("login.html")


# ----------------------------
# CADASTRO
# ----------------------------
@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        usuario = request.form["usuario"]
        senha = request.form["senha"]

        conn = conectar()
        c = conn.cursor()

        try:
            c.execute("INSERT INTO usuarios (usuario, senha) VALUES (?, ?)",
                      (usuario, senha))
            conn.commit()
            return redirect("/login")
        except:
            return "Usuário já existe"

    return render_template("cadastro.html")


# ----------------------------
# LOGOUT
# ----------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ----------------------------
# ADICIONAR TRANSAÇÃO
# ----------------------------
@app.route("/adicionar", methods=["POST"])
def adicionar():
    if "usuario" not in session:
        return redirect("/login")

    nome = request.form["nome"]
    valor = float(request.form["valor"])
    tipo = request.form["tipo"]

    conn = conectar()
    c = conn.cursor()

    c.execute("""
        INSERT INTO transacoes (usuario, nome, valor, tipo)
        VALUES (?, ?, ?, ?)
    """, (session["usuario"], nome, valor, tipo))

    conn.commit()

    return redirect("/")


# ----------------------------
# TRANSACOES
# ----------------------------
@app.route("/transacoes")
def listar():
    if "usuario" not in session:
        return redirect("/login")

    conn = conectar()
    c = conn.cursor()

    c.execute("SELECT * FROM transacoes WHERE usuario=?",
              (session["usuario"],))

    transacoes = c.fetchall()

    return render_template("transacoes.html", transacoes=transacoes)


if __name__ == "__main__":
    app.run(debug=True)