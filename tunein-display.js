/* Format uppercase ICY metadata for streams selected by the TuneIn picker. */
(() => {
    function stationLine(anchor, tag) {
        const line = document.createElement(tag);
        line.hidden = true;
        anchor.after(line);
        return line;
    }

    const stationLines = [
        stationLine(document.getElementById("PlaybackTitle"), "p"),
        stationLine(document.getElementById("footerTitle"), "div")
    ];
    const covers = ["PlaybackCover", "footerCover"].map(id => {
        const logo = document.createElement("img");
        logo.alt = "";
        logo.hidden = true;
        logo.classList.add("position-absolute", "top-0", "start-0", "w-100",
            "h-100", "object-fit-contain", "pe-none", "bg-body");
        logo.addEventListener("error", () => { logo.hidden = true; });
        document.getElementById(id).append(logo);
        return logo;
    });
    const assetBase = new URL(".", document.currentScript.src);
    const picker = document.createElement("button");
    picker.type = "button";
    picker.className = "btn px-2 mi rounded-2 d-none";
    picker.textContent = "tune";
    picker.title = "Open TuneIn station picker";
    picker.setAttribute("aria-label", picker.title);
    picker.addEventListener("click", () => {
        execScriptFromOptions("TuneIn Favorites", [""]);
    });
    document.getElementById("footerNextBtn")?.after(picker);

    function titleCase(value) {
        return value.split(/(\s+[-–—]\s+)/u).map(part => {
            if (part === part.toLowerCase() || part !== part.toUpperCase()) {
                return part;
            }
            return part.toLowerCase().replace(/(^|[^\p{L}\p{N}'’])(\p{L})/gu,
                (_, prefix, first) => prefix + first.toUpperCase());
        }).join("");
    }

    function update() {
        const fragment = (currentSongObj?.uri ?? "").split("#")[1] ?? "";
        const metadata = new URLSearchParams(fragment);
        const id = metadata.get("mympd-tunein") ?? "";
        const isTuneIn = /^s\d+$/.test(id);
        picker.classList.toggle("d-none", !isTuneIn);
        const stationName = metadata.get("name") ?? "";
        const artwork = metadata.get("art") ?? "";
        for (const line of stationLines) {
            line.hidden = !isTuneIn || stationName === "";
            if (!line.hidden) {
                line.textContent = stationName;
            }
        }
        const hasArtwork = isTuneIn && (artwork === id + ".jpg" || artwork === id + ".png");
        for (const logo of covers) {
            if (!hasArtwork) {
                logo.hidden = true;
                logo.removeAttribute("src");
            } else {
                const src = new URL("tunein-stations/" + artwork, assetBase).href;
                if (logo.src !== src) {
                    logo.src = src;
                    logo.hidden = false;
                }
            }
        }
        if (!isTuneIn) {
            return;
        }
        for (const id of ["PlaybackTitle", "footerTitle", "footerArtist"]) {
            const element = document.getElementById(id);
            if (element?.textContent) {
                const formatted = titleCase(element.textContent);
                if (formatted !== element.textContent) {
                    element.textContent = formatted;
                }
            }
        }
    }

    const observer = new MutationObserver(update);
    for (const id of ["PlaybackTitle", "footerTitle", "footerArtist"]) {
        const element = document.getElementById(id);
        if (element) {
            observer.observe(element, {childList: true, characterData: true, subtree: true});
        }
    }
    update();
})();
