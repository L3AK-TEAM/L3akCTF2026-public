(function startApp() {
  "use strict";

  const messageInput = document.getElementById("messageInput");
  const renderButton = document.getElementById("renderButton");
  const clearButton = document.getElementById("clearButton");
  const statusBadge = document.getElementById("statusBadge");
  const challengeMeta = document.getElementById("challengeMeta");
  const inputBytes = document.getElementById("inputBytes");
  const serverStatus = document.getElementById("serverStatus");
  const gallery = document.getElementById("gallery");

  let challenge = null;
  let renderToken = 0;

  function setStatus(text, mode) {
    statusBadge.textContent = text;
    statusBadge.className = mode ? "status " + mode : "status";
  }

  function utf8Length(message) {
    if (window.TextEncoder) {
      return new TextEncoder().encode(message).length;
    }

    return unescape(encodeURIComponent(message)).length;
  }

  function clearGallery() {
    gallery.replaceChildren();
  }

  function showBlocks(blocks) {
    clearGallery();

    for (const block of blocks) {
      const card = document.createElement("article");
      card.className = "blockCard";

      const frame = document.createElement("div");
      frame.className = "imageFrame";

      const image = document.createElement("img");
      image.className = "blockImage";
      image.alt = "Encrypted fractal block " + block.index;
      image.src = block.image;

      frame.append(image);
      card.append(frame);
      gallery.append(card);
    }
  }

  async function encryptMessage() {
    if (!challenge) {
      return;
    }

    const token = renderToken + 1;
    renderToken = token;
    renderButton.disabled = true;
    setStatus("Rendering", "warn");
    serverStatus.textContent = "pending";

    const message = messageInput.value;
    inputBytes.textContent = utf8Length(message) + " / " + challenge.publicConfig.maxInputBytes;

    try {
      const response = await fetch("/api/render", {
        method: "POST",
        headers: {
          "content-type": "application/json"
        },
        body: JSON.stringify({ message })
      });

      if (token !== renderToken) {
        return;
      }

      if (!response.ok) {
        const error = await response.json().catch(function noJson() {
          return { error: "Render failed" };
        });
        throw new Error(error.error || "Render failed");
      }

      const result = await response.json();
      serverStatus.textContent = result.blocks.length + " image" + (result.blocks.length === 1 ? "" : "s") + " returned";
      showBlocks(result.blocks);
      setStatus("Rendered", "good");
    } catch (error) {
      serverStatus.textContent = error.message;
      clearGallery();
      setStatus("Error", "warn");
    } finally {
      if (token === renderToken) {
        renderButton.disabled = false;
      }
    }
  }

  async function loadChallenge() {
    setStatus("Loading", "warn");
    renderButton.disabled = true;

    const response = await fetch("/api/challenge", {
      cache: "no-store"
    });

    if (!response.ok) {
      throw new Error("Challenge metadata failed to load");
    }

    challenge = await response.json();
    document.title = challenge.title || "Isaac's Kaleidoscope";
    challengeMeta.textContent = "A charmingly chromatic and cryptographically careless encryption service";
    inputBytes.textContent = "0 / " + challenge.publicConfig.maxInputBytes;
    serverStatus.textContent = "ready";
    renderButton.disabled = false;
    setStatus("Ready", "good");
  }

  renderButton.addEventListener("click", encryptMessage);
  clearButton.addEventListener("click", function clearMessage() {
    messageInput.value = "";
    inputBytes.textContent = challenge ? "0 / " + challenge.publicConfig.maxInputBytes : "-";
    serverStatus.textContent = challenge ? "ready" : "-";
    clearGallery();
    setStatus("Idle", "");
  });
  messageInput.addEventListener("keydown", function onKeydown(event) {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      encryptMessage();
    }
  });

  loadChallenge().catch(function handleLoadError(error) {
    challengeMeta.textContent = error.message;
    serverStatus.textContent = "unavailable";
    setStatus("Error", "warn");
  });
})();
