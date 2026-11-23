import "./globals.css";

// Metadados compartilhados pelas duas telas de acesso.
export const metadata = {
  title: "Meu Diário | Acesso",
  description: "Acesse seu espaço pessoal de cuidado e reflexão.",
};

// viewportFit habilita o uso de toda a tela no iPhone; o CSS respeita as safe areas.
export const viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  interactiveWidget: "resizes-content",
  themeColor: "#F7F7F2",
};

export default function RootLayout({ children }) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
