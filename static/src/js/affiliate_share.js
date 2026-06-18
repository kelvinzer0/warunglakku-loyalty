/**@odoo-module */
import { publicLoader } from "@web/public/assets_loader";

// Copy-to-clipboard handler for affiliate share buttons.
// Delegated click listener — survives re-renders from cart updates.
document.addEventListener("click", function (ev) {
    const btn = ev.target.closest(".wl_aff_share_copy");
    if (!btn) return;

    ev.preventDefault();
    const text = btn.getAttribute("data-clipboard-text") || "";
    if (!text) return;

    const done = () => {
        const originalHTML = btn.innerHTML;
        btn.classList.add("wl_aff_copied");
        btn.innerHTML = '<i class="fa fa-check"></i><span>Disalin!</span>';
        setTimeout(function () {
            btn.classList.remove("wl_aff_copied");
            btn.innerHTML = originalHTML;
        }, 1800);
    };

    const fail = () => {
        // Fallback: focus the read-only input next to the buttons so the
        // user can manually Cmd/Ctrl+C
        const input = btn.closest(".wl_aff_share")
            .querySelector(".wl_aff_share_link_input");
        if (input) {
            input.focus();
            input.select();
        }
    };

    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done, function () {
            fail();
        });
    } else {
        fail();
    }
});
