const form = document.getElementById("password-form");
const passwordOutput = document.getElementById("password-output");
const copyButton = document.getElementById("copy-button");
const clearButton = document.getElementById("clear-button");
const feedback = document.getElementById("feedback");
const lengthInput = document.getElementById("length");
const lengthValue = document.getElementById("length-value");
const strengthLabel = document.getElementById("strength-label");
const entropyValue = document.getElementById("entropy-value");

lengthInput.addEventListener("input", () => {
  lengthValue.textContent = lengthInput.value;
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  feedback.textContent = "Gerando senha segura...";

  const formData = new FormData(form);
  const payload = {
    length: Number(formData.get("length")),
    use_uppercase: formData.get("use_uppercase") === "on",
    use_lowercase: formData.get("use_lowercase") === "on",
    use_digits: formData.get("use_digits") === "on",
    use_symbols: formData.get("use_symbols") === "on",
  };

  const response = await fetch("/api/passwords", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const data = await response.json();

  if (!response.ok) {
    feedback.textContent = data.error || "Nao foi possivel gerar a senha.";
    return;
  }

  passwordOutput.value = data.password;
  strengthLabel.textContent = data.strength.label;
  entropyValue.textContent = `${data.strength.entropy} bits`;
  feedback.textContent = "Senha gerada com sucesso.";
});

copyButton.addEventListener("click", async () => {
  if (!passwordOutput.value) {
    feedback.textContent = "Gere uma senha antes de copiar.";
    return;
  }

  await navigator.clipboard.writeText(passwordOutput.value);
  feedback.textContent = "Senha copiada para a area de transferencia.";
});

clearButton.addEventListener("click", () => {
  passwordOutput.value = "";
  feedback.textContent = "Campos limpos.";
  strengthLabel.textContent = "Aguardando geração";
  entropyValue.textContent = "0 bits";
});
