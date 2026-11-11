(() => {
    const script = document.createElement("script");
    const url = new URL("browse/pics/tunein-display.js?v=4", document.currentScript.src).href;
    const policy = window.trustedTypes?.createPolicy("tunein-player", {
        createScriptURL(candidate) {
            if (candidate !== url) {
                throw new TypeError("Unexpected TuneIn script URL");
            }
            return url;
        }
    });
    script.src = policy ? policy.createScriptURL(url) : url;
    document.head.append(script);
})();
