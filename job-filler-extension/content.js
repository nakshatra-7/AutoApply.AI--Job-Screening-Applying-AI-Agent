(function () {
  if (typeof chrome === "undefined" || !chrome.runtime?.onMessage) {
    return;
  }

  function normalize(text) {
    return (text || "").toString().trim().toLowerCase();
  }

  function isVisible(el) {
    if (!el) return false;
    const rect = el.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
  }

  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  function clickElement(el) {
    if (!el) return;
    el.focus();
    ["pointerdown", "mousedown", "mouseup", "click"].forEach((type) => {
      el.dispatchEvent(new MouseEvent(type, { bubbles: true, cancelable: true, view: window }));
    });
  }

  function setNativeValue(element, value) {
    const { set: valueSetter } = Object.getOwnPropertyDescriptor(element, "value") || {};
    const prototype = Object.getPrototypeOf(element);
    const { set: prototypeSetter } = Object.getOwnPropertyDescriptor(prototype, "value") || {};
    if (prototypeSetter && valueSetter !== prototypeSetter) {
      prototypeSetter.call(element, value);
    } else if (valueSetter) {
      valueSetter.call(element, value);
    } else {
      element.value = value;
    }
  }

  function fillInput(input, value) {
    if (!input) return;
    input.focus();
    input.dispatchEvent(new Event("focus", { bubbles: true }));
    try {
      input.dispatchEvent(new InputEvent("beforeinput", { bubbles: true, data: value }));
    } catch (_err) {
      // Ignore beforeinput if not supported.
    }
    setNativeValue(input, value);
    input.setAttribute("value", value);
    try {
      input.dispatchEvent(new InputEvent("input", { bubbles: true, data: value }));
    } catch (_err) {
      input.dispatchEvent(new Event("input", { bubbles: true }));
    }
    input.dispatchEvent(new Event("change", { bubbles: true }));
    input.dispatchEvent(new KeyboardEvent("keyup", { bubbles: true, key: "Enter" }));
    input.dispatchEvent(new Event("blur", { bubbles: true }));
    input.setAttribute("aria-invalid", "false");
  }

  async function typeIntoInput(input, value, delayMs = 10) {
    if (!input) return false;
    input.focus();
    input.dispatchEvent(new Event("focus", { bubbles: true }));
    try {
      input.setSelectionRange(0, input.value.length);
    } catch (_err) {
      // Ignore selection errors.
    }
    setNativeValue(input, "");
    input.dispatchEvent(new Event("input", { bubbles: true }));
    const textValue = String(value || "");
    for (const char of textValue) {
      const key = char;
      input.dispatchEvent(new KeyboardEvent("keydown", { bubbles: true, key }));
      input.dispatchEvent(new KeyboardEvent("keypress", { bubbles: true, key }));
      setNativeValue(input, `${input.value}${char}`);
      try {
        input.dispatchEvent(new InputEvent("input", { bubbles: true, data: char }));
      } catch (_err) {
        input.dispatchEvent(new Event("input", { bubbles: true }));
      }
      input.dispatchEvent(new KeyboardEvent("keyup", { bubbles: true, key }));
      await sleep(delayMs);
    }
    input.dispatchEvent(new Event("change", { bubbles: true }));
    input.dispatchEvent(new Event("blur", { bubbles: true }));
    input.setAttribute("value", textValue);
    input.setAttribute("aria-invalid", "false");
    return true;
  }

  function commitInput(input) {
    if (!input) return;
    input.focus();
    input.dispatchEvent(new Event("focus", { bubbles: true }));
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
    input.dispatchEvent(new Event("focusout", { bubbles: true }));
    input.dispatchEvent(new KeyboardEvent("keydown", { bubbles: true, key: "Tab" }));
    input.dispatchEvent(new Event("blur", { bubbles: true }));
    input.setAttribute("value", input.value);
    input.setAttribute("aria-invalid", "false");
  }

  function nudgeInput(input) {
    if (!input) return;
    const current = input.value || "";
    const nudged = `${current} `;
    setNativeValue(input, nudged);
    input.dispatchEvent(new Event("input", { bubbles: true }));
    setNativeValue(input, current);
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
    input.dispatchEvent(new Event("blur", { bubbles: true }));
    input.setAttribute("value", current);
    input.setAttribute("aria-invalid", "false");
  }

  async function fillAllMatchingInputs(selectors, value, delayMs = 10) {
    const inputs = selectors.flatMap((selector) =>
      Array.from(document.querySelectorAll(selector))
    );
    let filled = false;
    for (const input of inputs) {
      if (!(input instanceof HTMLInputElement || input instanceof HTMLTextAreaElement)) {
        continue;
      }
      await typeIntoInput(input, value, delayMs);
      filled = true;
    }
    return filled;
  }

  function triggerFormChange() {
    const container =
      document.querySelector("[data-automation-id='applyFlowMyInfoPage']") ||
      document.querySelector("[data-automation-id='applyFlowPage']");
    if (!container) return;
    container.dispatchEvent(new Event("input", { bubbles: true }));
    container.dispatchEvent(new Event("change", { bubbles: true }));
  }

  async function fillInputWithRetry(input, value, attempts = 4) {
    if (!input) return false;
    for (let i = 0; i < attempts; i += 1) {
      fillInput(input, value);
      await sleep(250);
      if (normalize(input.value) === normalize(value)) {
        return true;
      }
    }
    return normalize(input.value) === normalize(value);
  }

  async function ensureFieldFilled(input, value, logs, label) {
    if (!input) return false;
    if (normalize(input.value)) return true;
    const ok = await fillInputWithRetry(input, value);
    if (!ok && label) {
      logs.push(`Could not confirm ${label}.`);
    }
    return ok;
  }

  function waitForListboxOptions(timeoutMs = 8000) {
    return new Promise((resolve) => {
      const start = Date.now();
      const timer = setInterval(() => {
        const options = Array.from(document.querySelectorAll("[role='listbox'] [role='option']"))
          .concat(Array.from(document.querySelectorAll("[data-automation-id='promptOption']")));
        if (options.length) {
          clearInterval(timer);
          resolve(options);
        }
        if (Date.now() - start > timeoutMs) {
          clearInterval(timer);
          resolve([]);
        }
      }, 200);
    });
  }

  function waitForInputsReady(timeoutMs = 12000) {
    return new Promise((resolve) => {
      const start = Date.now();
      const timer = setInterval(() => {
        const firstName = document.getElementById("name--legalName--firstName");
        const address1 = document.getElementById("address--addressLine1");
        const city = document.getElementById("address--city");
        const postal = document.getElementById("address--postalCode");
        const phone = document.getElementById("phoneNumber--phoneNumber");
        if (firstName && address1 && city && postal && phone) {
          clearInterval(timer);
          resolve(true);
        }
        if (Date.now() - start > timeoutMs) {
          clearInterval(timer);
          resolve(false);
        }
      }, 250);
    });
  }

  async function fillWithRetries(getter, value, attempts = 4) {
    for (let i = 0; i < attempts; i += 1) {
      const input = getter();
      if (!input) {
        await sleep(300);
        continue;
      }
      const isPhone = input.id?.includes("phoneNumber") || input.name === "phoneNumber";
      await typeIntoInput(input, value, isPhone ? 60 : 10);
      await sleep(300);
      if (normalize(input.value) === normalize(value)) {
        return true;
      }
    }
    return false;
  }

  function selectOptionExact(labelText) {
    const options = Array.from(document.querySelectorAll("[role='listbox'] [role='option']"))
      .concat(Array.from(document.querySelectorAll("[data-automation-id='promptOption']")));
    const match = options.find((el) => normalize(el.innerText) === normalize(labelText));
    if (match) {
      clickElement(match);
      return true;
    }
    return false;
  }

  function selectOptionContains(labelText) {
    const options = Array.from(document.querySelectorAll("[role='listbox'] [role='option']"))
      .concat(Array.from(document.querySelectorAll("[data-automation-id='promptOption']")));
    const match = options.find((el) => normalize(el.innerText).includes(normalize(labelText)));
    if (match) {
      clickElement(match);
      return true;
    }
    return false;
  }

  function selectOptionByAny(labels) {
    const options = Array.from(document.querySelectorAll("[role='listbox'] [role='option']"))
      .concat(Array.from(document.querySelectorAll("[data-automation-id='promptOption']")));
    for (const label of labels) {
      const match = options.find((el) => normalize(el.innerText).includes(normalize(label)));
      if (match) {
        clickElement(match);
        return true;
      }
    }
    return false;
  }

  function selectFirstValidOption() {
    const options = Array.from(document.querySelectorAll("[role='listbox'] [role='option']"))
      .concat(Array.from(document.querySelectorAll("[data-automation-id='promptOption']")));
    const match = options.find((el) => normalize(el.innerText) && !el.getAttribute("aria-disabled"));
    if (match) {
      clickElement(match);
      return true;
    }
    return false;
  }

  async function fillTextFieldByLabel(labelText, value, logs) {
    const field = Array.from(document.querySelectorAll("[data-automation-id^='formField']"))
      .find((el) => isVisible(el) && normalize(el.innerText).includes(normalize(labelText)));
    if (!field) return false;
    const input = field.querySelector("input[type='text'], input:not([type]), textarea");
    if (!input) return false;
    await fillInputWithRetry(input, value || "");
    field.dispatchEvent(new Event("input", { bubbles: true }));
    field.dispatchEvent(new Event("change", { bubbles: true }));
    logs.push(`Filled ${labelText}.`);
    return true;
  }

  async function selectDropdownByLabel(labelText, optionText, logs) {
    const field = Array.from(document.querySelectorAll("[data-automation-id^='formField']"))
      .find((el) => isVisible(el) && normalize(el.innerText).includes(normalize(labelText)));
    if (!field) return false;
    const button = field.querySelector("button[aria-haspopup='listbox']");
    if (!button) return false;
    clickElement(button);
    await waitForListboxOptions();
    if (selectOptionExact(optionText) || selectOptionContains(optionText) || selectFirstValidOption()) {
      logs.push(`Selected ${optionText} for ${labelText}.`);
      return true;
    }
    return false;
  }

  function findApplyButton() {
    const candidates = Array.from(document.querySelectorAll("button, a"))
      .filter((el) => normalize(el.innerText).includes("apply"));
    return candidates[0] || document.querySelector("[data-automation-id*='apply']");
  }

  function findApplyManuallyButton() {
    return (
      Array.from(document.querySelectorAll("button, a")).find((el) =>
        normalize(el.innerText).includes("apply manually")
      ) ||
      document.querySelector("[data-automation-id*='applyManually'], [data-automation-id*='apply-manually']")
    );
  }

  async function clickApplyManually(logs) {
    const manualBtn = findApplyManuallyButton();
    if (manualBtn) {
      clickElement(manualBtn);
      logs.push("Clicked Apply Manually.");
      return true;
    }
    return false;
  }

  function waitForForm(timeoutMs = 20000) {
    return new Promise((resolve, reject) => {
      const start = Date.now();
      const timer = setInterval(() => {
        const form = document.querySelector("form");
        const applyFlow = document.querySelector(
          "[data-automation-id='applyFlowPage'], [data-automation-id='applyFlowMyInfoPage']"
        );
        if (form || applyFlow) {
          clearInterval(timer);
          resolve();
        }
        if (Date.now() - start > timeoutMs) {
          clearInterval(timer);
          reject(new Error("Timed out waiting for application form."));
        }
      }, 400);
    });
  }

  async function selectSourceLinkedIn(logs) {
    const sourceInput = document.getElementById("source--source");
    if (!sourceInput) return false;
    const promptIcon = document.querySelector(
      "[data-automation-id='formField-source'] [data-automation-id='promptIcon']"
    );
    if (promptIcon) {
      clickElement(promptIcon);
      await sleep(200);
    }
    clickElement(sourceInput);
    await waitForListboxOptions();
    if (!selectOptionExact("Social Network")) {
      if (!selectOptionExact("Social Media")) {
        selectOptionContains("social");
      }
    }
    await sleep(1500);
    await waitForListboxOptions(12000);
    if (selectOptionByAny(["LinkedIn Job Board", "LinkedIn", "Job Board"])) {
      await sleep(200);
      const selected = Array.from(document.querySelectorAll("[data-automation-id='selectedItem']"))
        .some((el) => normalize(el.innerText).includes("linkedin"));
      if (selected) {
        logs.push("Selected source: LinkedIn.");
        return true;
      }
    }

    await sleep(1000);
    clickElement(sourceInput);
    await waitForListboxOptions(12000);
    if (selectOptionByAny(["LinkedIn Job Board", "LinkedIn", "Job Board"])) {
      await sleep(200);
      const selectedRetry = Array.from(document.querySelectorAll("[data-automation-id='selectedItem']"))
        .some((el) => normalize(el.innerText).includes("linkedin"));
      if (selectedRetry) {
        logs.push("Selected source: LinkedIn.");
        return true;
      }
    }

    fillInput(sourceInput, "LinkedIn Job Board");
    sourceInput.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    await sleep(200);
    const selectedFallback = Array.from(document.querySelectorAll("[data-automation-id='selectedItem']"))
      .some((el) => normalize(el.innerText).includes("linkedin"));
    if (selectedFallback) {
      logs.push("Selected source: LinkedIn.");
      return true;
    }

    logs.push("Could not select source.");
    return false;
  }

  async function selectCountryAndPhoneCode(profile, logs) {
    const countryBtn = document.getElementById("country--country");
    if (countryBtn) {
      clickElement(countryBtn);
      await waitForListboxOptions();
      if (!selectOptionExact(profile.country || "India")) {
        selectOptionContains("india");
      }
      logs.push("Selected country.");
    }

    const phoneCodeInput = document.getElementById("phoneNumber--countryPhoneCode");
    if (phoneCodeInput) {
      clickElement(phoneCodeInput);
      await waitForListboxOptions();
      if (!selectOptionExact("India (+91)")) {
        selectOptionContains("india (+91)") || selectOptionContains("(+91)") || selectOptionContains("india");
      }
      logs.push("Selected country phone code.");
    }
  }

  async function selectPhoneType(logs) {
    const phoneTypeBtn = document.getElementById("phoneNumber--phoneType");
    if (!phoneTypeBtn) return;
    clickElement(phoneTypeBtn);
    await waitForListboxOptions();
    if (selectOptionExact("Mobile") || selectOptionContains("mobile")) {
      logs.push("Selected phone type: Mobile.");
    }
  }

  async function selectAuthorizedToWork(logs) {
    const field = Array.from(document.querySelectorAll("[data-automation-id^='formField']"))
      .find((el) => normalize(el.innerText).includes("authorized to work"));
    if (!field) return false;
    const button = field.querySelector("button[aria-haspopup='listbox']");
    if (!button) return false;
    clickElement(button);
    await waitForListboxOptions();
    if (selectOptionExact("Yes") || selectOptionContains("yes")) {
      logs.push("Selected work authorization: Yes.");
      return true;
    }
    return false;
  }

  function findFieldByLabel(labelText) {
    const normalized = normalize(labelText);
    return Array.from(document.querySelectorAll("[data-automation-id^='formField']")).find((el) =>
      normalize(el.innerText).includes(normalized)
    );
  }

  async function selectDropdownByLabelText(labelText, optionText, logs) {
    const field = findFieldByLabel(labelText);
    if (!field) return false;
    const button = field.querySelector("button[aria-haspopup='listbox']");
    if (!button) return false;
    clickElement(button);
    await waitForListboxOptions(12000);
    if (selectOptionExact(optionText) || selectOptionContains(optionText) || selectFirstValidOption()) {
      logs.push(`Selected ${optionText} for ${labelText}.`);
      return true;
    }
    return false;
  }


  async function fillBasicFields(profile, logs) {
    const address1 = document.getElementById("address--addressLine1");
    const city = document.getElementById("address--city");
    const postal = document.getElementById("address--postalCode");
    const phone = document.getElementById("phoneNumber--phoneNumber");
    const firstName = document.getElementById("name--legalName--firstName");
    const lastName = document.getElementById("name--legalName--lastName");

    await typeIntoInput(firstName, profile.first_name || "");
    await typeIntoInput(lastName, profile.last_name || "");
    await typeIntoInput(address1, profile.address_line1 || "");
    await typeIntoInput(city, profile.city || "");
    await typeIntoInput(postal, profile.postal_code || "");
    await typeIntoInput(phone, profile.phone || "", 60);
    logs.push("Filled profile fields.");

    await fillTextFieldByLabel("Given Name", profile.first_name || "", logs);
    await fillTextFieldByLabel("Family Name", profile.last_name || "", logs);
    await fillTextFieldByLabel("Address Line 1", profile.address_line1 || "", logs);
    await fillTextFieldByLabel("City", profile.city || "", logs);
    await fillTextFieldByLabel("Postal Code", profile.postal_code || "", logs);
    await fillTextFieldByLabel("Phone Number", profile.phone || "", logs);
  }

  function findResumeUploadButton() {
    return (
      document.querySelector("[data-automation-id='select-files']") ||
      document.querySelector("[data-automation-id='resumeAttachments--attachments']") ||
      document.querySelector("[data-automation-id='file-upload-drop-zone'] button") ||
      Array.from(document.querySelectorAll("button, [role='button']")).find((el) =>
        normalize(el.innerText).includes("select files")
      ) ||
      Array.from(document.querySelectorAll("button, [role='button']")).find((el) =>
        normalize(el.getAttribute("aria-label")).includes("select files")
      )
    );
  }

  function setupResumeAutoContinue(delayMs = 10000) {
    const input = document.querySelector("input[type='file']");
    if (!input || input.dataset.autoContinueBound === "true") return;
    input.dataset.autoContinueBound = "true";
    input.addEventListener("change", () => {
      if (!input.value) return;
      setTimeout(() => {
        const nextBtn = document.querySelector("[data-automation-id='pageFooterNextButton']");
        if (nextBtn) {
          clickElement(nextBtn);
          document.body.dataset.autoContinueDone = "true";
        }
      }, delayMs);
    });
  }

  function scheduleResumeContinue(delayMs = 10000) {
    const root = document.body;
    if (!root || root.dataset.resumeContinueScheduled === "true") return;
    root.dataset.resumeContinueScheduled = "true";
    setTimeout(() => {
      const nextBtn = document.querySelector("[data-automation-id='pageFooterNextButton']");
      if (nextBtn) {
        clickElement(nextBtn);
        root.dataset.autoContinueDone = "true";
      }
    }, delayMs);
  }

  function waitForAccountForm(timeoutMs = 15000) {
    return new Promise((resolve, reject) => {
      const start = Date.now();
      const timer = setInterval(() => {
        const email = document.querySelector("input[data-automation-id='email']");
        const password = document.querySelector("input[data-automation-id='password']");
        const confirm = document.querySelector("input[data-automation-id='verifyPassword']");
        const checkbox = document.querySelector("input[data-automation-id='createAccountCheckbox']");
        const submit =
          document.querySelector("[data-automation-id='createAccountSubmitButton']") ||
          document.querySelector("[data-automation-id='click_filter']") ||
          document.querySelector("button[type='submit']");
        if (email && password && confirm && submit) {
          clearInterval(timer);
          resolve({ email, password, confirm, checkbox, submit });
        }
        if (Date.now() - start > timeoutMs) {
          clearInterval(timer);
          reject(new Error("Timed out waiting for create account form."));
        }
      }, 400);
    });
  }

  async function fillCreateAccount(account, logs) {
    if (!account?.email || !account?.password) return false;
    const { email, password, confirm, checkbox, submit } = await waitForAccountForm();
    fillInput(email, account.email);
    fillInput(password, account.password);
    fillInput(confirm, account.confirmPassword || account.password);
    if (checkbox && !checkbox.checked) {
      clickElement(checkbox);
      checkbox.checked = true;
      checkbox.dispatchEvent(new Event("change", { bubbles: true }));
      logs.push("Checked terms/consent checkbox.");
    }
    let clicked = false;
    if (submit) {
      clickElement(submit);
      clicked = true;
    }
    const clickFilter = document.querySelector("[data-automation-id='click_filter']");
    if (clickFilter) {
      clickElement(clickFilter);
      clicked = true;
    }
    const hiddenSubmit = document.querySelector("[data-automation-id='createAccountSubmitButton']");
    if (hiddenSubmit) {
      clickElement(hiddenSubmit);
      clicked = true;
    }
    const form = email?.closest("form") || document.querySelector("form");
    if (form && typeof form.requestSubmit === "function") {
      form.requestSubmit();
      clicked = true;
    }
    if (clicked) {
      logs.push("Clicked Create Account.");
    } else {
      logs.push("Create Account button not found.");
    }
    return true;
  }

  function waitForSignInForm(timeoutMs = 15000) {
    return new Promise((resolve, reject) => {
      const start = Date.now();
      const timer = setInterval(() => {
        const email = document.querySelector("input[data-automation-id='email']");
        const pass = document.querySelector("input[data-automation-id='password']");
        const signIn =
          document.querySelector("[data-automation-id='signInSubmitButton']") ||
          document.querySelector("[data-automation-id='signInButton']") ||
          document.querySelector("[data-automation-id='click_filter'][aria-label='Sign In']") ||
          Array.from(document.querySelectorAll("button")).find((btn) =>
            normalize(btn.innerText).includes("sign in")
          );
        if (email && pass && signIn) {
          clearInterval(timer);
          resolve({ email, pass, signIn });
        }
        if (Date.now() - start > timeoutMs) {
          clearInterval(timer);
          reject(new Error("Timed out waiting for sign-in form."));
        }
      }, 400);
    });
  }

  async function fillSignIn(account, logs) {
    if (!account?.email || !account?.password) return false;
    const { email, pass, signIn } = await waitForSignInForm();
    fillInput(email, account.email);
    fillInput(pass, account.password);
    let clicked = false;
    if (signIn) {
      clickElement(signIn);
      clicked = true;
    }
    if (signIn && typeof signIn.click === "function") {
      signIn.click();
      clicked = true;
    }
    const overlay = document.querySelector("[data-automation-id='click_filter'][aria-label='Sign In']");
    if (overlay) {
      clickElement(overlay);
      clicked = true;
    }
    const form = email?.closest("form") || document.querySelector("form");
    if (form && typeof form.requestSubmit === "function") {
      form.requestSubmit();
      clicked = true;
    }
    if (clicked) {
      logs.push("Filled sign-in form and clicked Sign In.");
    } else {
      logs.push("Sign In button not found.");
    }
    return true;
  }

  async function applyAndFillWorkday(packet, profile, account) {
    if (document.body?.dataset.autoContinueDone === "true") {
      return { ok: true, logs: ["Auto-continued after file upload; waiting for next Apply click."] };
    }
    const logs = [];
    const applyBtn = findApplyButton();
    if (applyBtn) {
      clickElement(applyBtn);
      logs.push("Found Apply button. Clicking...");
    }

    await sleep(1200);
    await clickApplyManually(logs);

    try {
      await fillCreateAccount(account, logs);
    } catch (_err) {
      // Not on create account step; continue.
    }

    try {
      await fillSignIn(account, logs);
    } catch (_err) {
      // Not on sign-in step; continue.
    }

    await waitForForm();
    logs.push("Form detected. Filling fields...");
    await waitForInputsReady();

    const sourceSelected = await selectSourceLinkedIn(logs);
    const noInput = document.querySelector("input[name='candidateIsPreviousWorker'][value='false']");
    const noLabel = noInput ? document.querySelector(`label[for='${noInput.id}']`) : null;
    if (noLabel) {
      clickElement(noLabel);
      logs.push("Selected previous worker: No.");
    } else if (noInput) {
      clickElement(noInput);
      noInput.checked = true;
      noInput.dispatchEvent(new Event("change", { bubbles: true }));
      logs.push("Selected previous worker: No.");
    }
    await selectDropdownByLabel("How Did You Hear About Us", "Social Network", logs);
    await selectCountryAndPhoneCode(profile || {}, logs);
    await selectPhoneType(logs);
    await fillBasicFields(profile || {}, logs);
    await selectAuthorizedToWork(logs);
    await selectDropdownByLabelText("require sponsorship", "No", logs);
    await selectDropdownByLabelText("willing to relocate", "Yes", logs);
    await selectDropdownByLabelText("what is your notice period", "90 or More Days", logs);
    await selectDropdownByLabelText("types of schedules you are willing to work", "Onsite/In-Office", logs);
    await selectDropdownByLabelText(
      "personal relations or blood relatives, currently employed by s&p global",
      "No",
      logs
    );
    await selectDropdownByLabelText("identify your gender", "Male", logs);
    await selectDropdownByLabelText("pronoun", "He/Him", logs);
    const policyField = findFieldByLabel("acknowledge that i have read and understand the policy");
    const policyCheckbox = policyField?.querySelector("input[type='checkbox']");
    if (policyCheckbox && !policyCheckbox.checked) {
      clickElement(policyCheckbox);
      policyCheckbox.checked = true;
      policyCheckbox.dispatchEvent(new Event("change", { bubbles: true }));
      logs.push("Checked policy acknowledgement.");
    }

    if (!sourceSelected) {
      await sleep(2000);
      await selectSourceLinkedIn(logs);
    }

    await fillWithRetries(
      () => document.getElementById("name--legalName--firstName"),
      profile.first_name || ""
    );
    await fillWithRetries(
      () => document.getElementById("name--legalName--lastName"),
      profile.last_name || ""
    );
    await fillWithRetries(
      () => document.getElementById("address--addressLine1"),
      profile.address_line1 || ""
    );
    await fillWithRetries(
      () => document.getElementById("address--city"),
      profile.city || ""
    );
    const postalValue = String(profile.postal_code || "").replace(/\D/g, "");
    await fillWithRetries(
      () => document.getElementById("address--postalCode"),
      postalValue
    );
    await fillWithRetries(
      () => document.getElementById("phoneNumber--phoneNumber"),
      profile.phone || ""
    );

    await fillAllMatchingInputs(
      ["#name--legalName--firstName", "input[name='legalName--firstName']"],
      profile.first_name || ""
    );
    await fillAllMatchingInputs(
      ["#address--addressLine1", "input[name='addressLine1']"],
      profile.address_line1 || ""
    );
    await fillAllMatchingInputs(
      ["#address--city", "input[name='city']"],
      profile.city || ""
    );
    await fillAllMatchingInputs(
      ["#address--postalCode", "input[name='postalCode']"],
      postalValue
    );
    await fillAllMatchingInputs(
      ["#phoneNumber--phoneNumber", "input[name='phoneNumber']"],
      profile.phone || "",
      60
    );

    triggerFormChange();
    commitInput(document.getElementById("name--legalName--firstName"));
    commitInput(document.getElementById("address--city"));
    commitInput(document.getElementById("address--postalCode"));
    commitInput(document.getElementById("phoneNumber--phoneNumber"));
    nudgeInput(document.getElementById("name--legalName--firstName"));
    nudgeInput(document.getElementById("address--addressLine1"));
    nudgeInput(document.getElementById("address--city"));
    // Skip nudge for postal code to avoid validation glitches.
    await sleep(800);

    await sleep(400);
    const uploadButton = findResumeUploadButton();
    if (uploadButton) {
      const resumeInput = document.querySelector("input[type='file']");
      if (!resumeInput || !resumeInput.value) {
        setupResumeAutoContinue(10000);
        if (document.body?.dataset.resumePickerOpened === "true") {
          logs.push("Resume picker already opened; waiting for file selection.");
          return { ok: true, logs, blocked: "resume_upload" };
        }
        clickElement(uploadButton);
        logs.push("Resume upload required. Please select your resume file to continue.");
        return { ok: true, logs, blocked: "resume_upload" };
      }
    }
    const resumeInput = document.querySelector("input[type='file']");
    if (resumeInput && !resumeInput.value) {
      setupResumeAutoContinue(10000);
      const dropZone = document.querySelector("[data-automation-id='file-upload-drop-zone']");
      if (dropZone) {
        clickElement(dropZone);
        logs.push("Resume upload required. Clicked drop zone; select your resume file to continue.");
        return { ok: true, logs, blocked: "resume_upload" };
      }
      logs.push("Resume upload required but Select Files button not found.");
      return { ok: true, logs, blocked: "resume_upload" };
    }

    const nextBtn = document.querySelector("[data-automation-id='pageFooterNextButton']");
    if (nextBtn) {
      clickElement(nextBtn);
      logs.push("Clicked Save and Continue.");
    }

    logs.push("Fill complete. Review before submitting.");
    return { ok: true, logs };
  }

  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg?.type !== "EXTRACT_JD") return;
    const job_description = document.body?.innerText || "";
    sendResponse({
      ok: true,
      url: location.href,
      job_description,
      job_title: document.title || "",
      company: ""
    });
    return true;
  });

  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg?.type !== "APPLY_AND_FILL") return;
    applyAndFillWorkday(msg.packet || {}, msg.profile || {}, msg.account || {})
      .then((res) => sendResponse(res))
      .catch((err) => sendResponse({ ok: false, error: err.message || String(err), logs: [] }));
    return true;
  });

  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg?.type !== "OPEN_RESUME_PICKER") return;
    const root = document.body;
    if (root?.dataset.resumePickerOpened === "true") {
      return sendResponse({ ok: true, note: "Picker already opened." });
    }
    const uploadButton = findResumeUploadButton();
    if (uploadButton) {
      if (root) root.dataset.resumePickerOpened = "true";
      clickElement(uploadButton);
      setupResumeAutoContinue(10000);
      return sendResponse({ ok: true });
    }
    const dropZone = document.querySelector("[data-automation-id='file-upload-drop-zone']");
    if (dropZone) {
      if (root) root.dataset.resumePickerOpened = "true";
      clickElement(dropZone);
      setupResumeAutoContinue(10000);
      return sendResponse({ ok: true });
    }
    return sendResponse({ ok: false, error: "Select files button not found." });
  });

  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg?.type !== "CONTINUE_AFTER_RESUME") return;
    applyAndFillWorkday(msg.packet || {}, msg.profile || {}, msg.account || {})
      .then((res) => sendResponse(res))
      .catch((err) => sendResponse({ ok: false, error: err.message || String(err), logs: [] }));
    return true;
  });
})();
