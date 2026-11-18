"use client";

import { useState } from "react";

const emailValido = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// Formulário simples compartilhado; a rota selecionada depende do modo da tela.
export default function AuthForm({ mode }) {
  const cadastro = mode === "cadastro";
  const [mostrarSenha, setMostrarSenha] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [aviso, setAviso] = useState(null);

  async function enviarFormulario(event) {
    event.preventDefault();
    const dados = new FormData(event.currentTarget);
    const nome = String(dados.get("nome") || "").trim();
    const email = String(dados.get("email") || "").trim().toLowerCase();
    const senha = String(dados.get("senha") || "");
    const confirmacao = String(dados.get("confirmacao") || "");

    // Mensagens curtas explicam como corrigir cada erro antes de chamar o servidor.
    if (cadastro && nome.length < 2) {
      setAviso({ tipo: "erro", texto: "Informe um nome com pelo menos 2 caracteres." });
      return;
    }
    if (!emailValido.test(email)) {
      setAviso({ tipo: "erro", texto: "Confira se o e-mail foi digitado corretamente." });
      return;
    }
    if (!senha || (cadastro && senha.length < 8)) {
      setAviso({
        tipo: "erro",
        texto: cadastro
          ? "Escolha uma senha entre 8 e 128 caracteres."
          : "Informe sua senha para continuar.",
      });
      return;
    }
    if (cadastro && senha !== confirmacao) {
      setAviso({ tipo: "erro", texto: "As senhas não coincidem. Confira os dois campos." });
      return;
    }

    setEnviando(true);
    setAviso(null);

    try {
      const resposta = await fetch(`/api/auth/${cadastro ? "cadastro" : "login"}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify(
          cadastro ? { nome, email, senha } : { email, senha },
        ),
      });
      const resultado = await resposta.json().catch(() => ({}));

      if (!resposta.ok) {
        setAviso({
          tipo: "erro",
          texto: resultado.message || "Não foi possível concluir agora. Tente novamente em instantes.",
        });
        return;
      }

      setAviso({
        tipo: "sucesso",
        texto:
          resultado.message ||
          (cadastro
            ? "Cadastro enviado. Agora você já pode entrar com seus dados."
            : "Acesso realizado com sucesso."),
      });
    } catch {
      setAviso({
        tipo: "erro",
        texto: "Não foi possível conectar ao serviço agora. Tente novamente em instantes.",
      });
    } finally {
      setEnviando(false);
    }
  }

  function lembrarAjuda() {
    setAviso({
      tipo: "ajuda",
      texto: "Para recuperar seu acesso, peça ajuda ao profissional que acompanha você.",
    });
  }

  return (
    <form className="auth-form" onSubmit={enviarFormulario} noValidate>
      {cadastro && (
        <div className="form-field">
          <label htmlFor="nome">Nome completo</label>
          <input
            autoComplete="name"
            id="nome"
            name="nome"
            placeholder="Como podemos chamar você?"
            maxLength={120}
            required
          />
        </div>
      )}

      <div className="form-field">
        <label htmlFor="email">E-mail</label>
        <input
          autoComplete="email"
          autoCapitalize="none"
          id="email"
          name="email"
          placeholder="voce@exemplo.com"
          type="email"
          inputMode="email"
          maxLength={254}
          required
        />
      </div>

      <div className="form-field">
        <label htmlFor="senha">Senha</label>
        <div className="password-field">
          <input
            autoComplete={cadastro ? "new-password" : "current-password"}
            id="senha"
            name="senha"
            placeholder={cadastro ? "De 8 a 128 caracteres" : "Digite sua senha"}
            type={mostrarSenha ? "text" : "password"}
            minLength={cadastro ? 8 : undefined}
            maxLength={128}
            required
          />
          <button
            className="password-toggle"
            type="button"
            aria-label={mostrarSenha ? "Ocultar senha" : "Mostrar senha"}
            aria-pressed={mostrarSenha}
            onClick={() => setMostrarSenha((atual) => !atual)}
          >
            {mostrarSenha ? "Ocultar" : "Mostrar"}
          </button>
        </div>
      </div>

      {cadastro ? (
        <div className="form-field">
          <label htmlFor="confirmacao">Confirme sua senha</label>
          <input
            autoComplete="new-password"
            id="confirmacao"
            name="confirmacao"
            placeholder="Digite a senha novamente"
            type={mostrarSenha ? "text" : "password"}
            minLength={8}
            maxLength={128}
            required
          />
        </div>
      ) : (
        <div className="form-options">
          <span>Seu espaço, no seu tempo.</span>
          <button className="text-link" type="button" onClick={lembrarAjuda}>
            Esqueci minha senha
          </button>
        </div>
      )}

      {aviso && (
        <p
          className={`form-feedback ${aviso.tipo}`}
          role={aviso.tipo === "erro" ? "alert" : "status"}
          aria-live="polite"
        >
          {aviso.texto}
        </p>
      )}

      <button className="submit-button" type="submit" disabled={enviando}>
        {enviando ? "Aguarde…" : cadastro ? "Criar meu acesso" : "Entrar no meu diário"}
      </button>
      {cadastro && <p className="form-hint">Você poderá alterar seus dados depois.</p>}
    </form>
  );
}
