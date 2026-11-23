import Link from "next/link";

// Moldura compartilhada para manter login e cadastro com a mesma identidade visual.
export default function AuthShell({ eyebrow, title, description, footer, children }) {
  return (
    <main className="auth-layout">
      {/* Painel de acolhimento: no celular ele se transforma em um cabeçalho compacto. */}
      <section className="story-panel" aria-label="Um espaço de cuidado">
        <Link className="brand" href="/" aria-label="Meu Diário, página inicial">
          <span className="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 32 32" fill="none">
              <path d="M16 26V13m0 6c-5.5 0-8-3.5-8-8 5.5 0 8 3.5 8 8Zm0-4c0-5.1 3.1-8 8-8 0 5.6-2.8 8-8 8Z" />
            </svg>
          </span>
          <span className="brand-name">meu diário</span>
        </Link>

        <div className="story-copy">
          <p className="story-kicker">UM ESPAÇO SEU</p>
          <h2>Um passo de cada vez.</h2>
          <p>
            Um lugar tranquilo para registrar o que você sente, no seu tempo e com
            acolhimento.
          </p>
        </div>

        <div className="story-note">
          <span className="note-mark" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none">
              <path d="M12 20s-7-4.3-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.7-7 10-7 10Z" />
            </svg>
          </span>
          <p>Suas palavras merecem ser acolhidas.</p>
        </div>
        <span className="story-orb story-orb-one" aria-hidden="true" />
        <span className="story-orb story-orb-two" aria-hidden="true" />
      </section>

      {/* Cartão do formulário com largura confortável em telas grandes e pequenas. */}
      <section className="form-side">
        <div className="auth-card">
          <p className="form-eyebrow">{eyebrow}</p>
          <h1>{title}</h1>
          <p className="form-description">{description}</p>
          {children}
          <div className="auth-footer">{footer}</div>
        </div>
        <p className="privacy-note">
          Um espaço de cuidado. Use seus dados apenas para acessar sua conta.
        </p>
      </section>
    </main>
  );
}
