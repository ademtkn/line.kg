# Self-hosted font sources

Downloaded on 2026-10-14 from the official Google Fonts CSS API and fonts.gstatic.com. Font binaries are retained without modification.

CSS API request:

https://fonts.googleapis.com/css2?family=Manrope:wght@200..800&family=Plus+Jakarta+Sans:wght@200..800&display=swap

Normal variable weight range: **200–800**. `font-display: swap` is used.

Included subsets: Manrope Latin, Cyrillic and Cyrillic-ext; Plus Jakarta Sans Latin. Manrope is the intended Cyrillic fallback for headings. Manrope Cyrillic-ext covers Ө/ө (U+04E8/U+04E9) and Ү/ү (U+04AE/U+04AF), but its actual cmap lacks Ң/ң (U+04A2/U+04A3). A two-character Noto Sans subset provides these missing Kyrgyz glyphs. The intended CSS fallback order is `"Manrope", "Noto Sans", sans-serif` for body and `"Plus Jakarta Sans", "Manrope", "Noto Sans", sans-serif` for headings.

## Files

- `manrope-cyrillic-ext-variable.woff2` — 2592 bytes; source: https://fonts.gstatic.com/s/manrope/v20/xn7gYHE41ni1AdIRggqxSvfedN62Zw.woff2
- `manrope-cyrillic-variable.woff2` — 14544 bytes; source: https://fonts.gstatic.com/s/manrope/v20/xn7gYHE41ni1AdIRggOxSvfedN62Zw.woff2
- `manrope-latin-variable.woff2` — 24576 bytes; source: https://fonts.gstatic.com/s/manrope/v20/xn7gYHE41ni1AdIRggexSvfedN4.woff2
- `plus-jakarta-sans-latin-variable.woff2` — 27272 bytes; source: https://fonts.gstatic.com/s/plusjakartasans/v12/LDIoaomQNQcsA88c7O9yZ4KMCoOg4Ko20yygg_vb.woff2
- `Manrope-OFL.txt` — 4387 bytes; source: https://raw.githubusercontent.com/google/fonts/main/ofl/manrope/OFL.txt
- `PlusJakartaSans-OFL.txt` — 4402 bytes; source: https://raw.githubusercontent.com/google/fonts/main/ofl/plusjakartasans/OFL.txt

## Licenses

Manrope and Plus Jakarta Sans are distributed under the SIL Open Font License 1.1. Complete license notices are preserved in `Manrope-OFL.txt` and `PlusJakartaSans-OFL.txt`. These license files were downloaded from the official google/fonts repository:

- https://github.com/google/fonts/tree/main/ofl/manrope
- https://github.com/google/fonts/tree/main/ofl/plusjakartasans

## CSS API reference

https://developers.google.com/fonts/docs/css2

## Kyrgyz Ң/ң fallback

Official Google Fonts API subset request: https://fonts.googleapis.com/css2?family=Noto+Sans:wght@200..800&display=swap&text=%D2%A2%D2%A3

- `noto-sans-kyrgyz-n-variable.woff2` — 2304 bytes; source: https://fonts.gstatic.com/l/font?kit=o-0bIpQlx3QUlC5A4PNB6Ryti20_6n1iPHjc1azXvFujBSmvKfKW&skey=2b960fe17823056f&v=v42
- `NotoSans-OFL.txt` — 4396 bytes; source: https://raw.githubusercontent.com/google/fonts/main/ofl/notosans/OFL.txt

Noto Sans uses SIL Open Font License 1.1, preserved without modification. Only U+04A2/U+04A3 are declared in CSS. This font binary is not edited after downloading the official Google Fonts subset.
