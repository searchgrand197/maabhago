import os
import smtplib
import ssl
from email.message import EmailMessage


ENV_EXAMPLE_PATH = os.path.join(os.path.dirname(__file__), ".env.example")


def load_env_example(path: str) -> dict:
    data: dict[str, str] = {}
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} not found")
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            data[key.strip()] = value.strip()
    return data


def main():
    env = load_env_example(ENV_EXAMPLE_PATH)

    host = env.get("EMAIL_HOST", "")
    port = int(env.get("EMAIL_PORT", "25"))
    use_ssl = env.get("EMAIL_USE_SSL", "False").lower() == "true"
    use_tls = env.get("EMAIL_USE_TLS", "False").lower() == "true"
    user = env.get("EMAIL_HOST_USER", "")
    password = env.get("EMAIL_HOST_PASSWORD", "")
    from_email = env.get("DEFAULT_FROM_EMAIL", user or "no-reply@example.com")

    print("Using email settings from .env.example:")
    print("  EMAIL_HOST:", host)
    print("  EMAIL_PORT:", port)
    print("  EMAIL_USE_SSL:", use_ssl)
    print("  EMAIL_USE_TLS:", use_tls)
    print("  EMAIL_HOST_USER:", user)
    print("  DEFAULT_FROM_EMAIL:", from_email)

    to_email = "searchgrand@gmail.com"

    msg = EmailMessage()
    msg["Subject"] = "HMS test email via .env.example"
    msg["From"] = from_email
    msg["To"] = to_email

    text_body = (
        "Hi,\n\n"
        "This is a test email sent using SMTP settings read from .env.example.\n\n"
        f"Host: {host}\n"
        f"Port: {port}\n\n"
        "If you can read this, the SMTP configuration is working.\n\n"
        "Best regards,\n"
        "HMS\n"
    )
    html_body = f"""
    <html>
      <body>
        <p>Hi,</p>
        <p>This is a <strong>test email</strong> sent using SMTP settings read from <code>.env.example</code>.</p>
        <ul>
          <li>Host: <code>{host}</code></li>
          <li>Port: <code>{port}</code></li>
        </ul>
        <p>If you can read this, the SMTP configuration is working.</p>
        <p>Best regards,<br/>HMS</p>
      </body>
    </html>
    """

    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    if use_ssl:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, context=context) as server:
            if user and password:
                server.login(user, password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(host, port) as server:
            if use_tls:
                server.starttls()
            if user and password:
                server.login(user, password)
            server.send_message(msg)

    print("Test email sent to", to_email)


if __name__ == "__main__":
    main()