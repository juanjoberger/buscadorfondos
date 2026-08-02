/* Pobla los selects de país, región y comuna/ciudad.
   Carga lazy: la lista de países primero y las regiones/ciudades solo del
   país elegido (/api/ubicaciones/<pais>), porque el catálogo LATAM completo
   pesa ~370 KB. */
(async function () {
  const paisSelect = document.getElementById("pais");
  const regionSelect = document.getElementById("region");
  const comunaSelect = document.getElementById("comuna");
  if (!regionSelect) return;

  async function getJSON(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error(url + " → " + res.status);
    return res.json();
  }

  const paisActual = paisSelect ? (paisSelect.dataset.seleccionada || "Chile") : "Chile";
  const regionActual = regionSelect.dataset.seleccionada || "";
  const comunaActual = comunaSelect ? (comunaSelect.dataset.seleccionada || "") : "";
  let regiones = {}; // región → [ciudades] del país elegido

  function repoblar(select, valores, preseleccion) {
    if (!select) return;
    const primera = select.querySelector("option"); // conserva "Todas…"
    select.innerHTML = "";
    if (primera) select.appendChild(primera);
    valores.forEach((v) => {
      const opt = document.createElement("option");
      opt.value = v;
      opt.textContent = v;
      if (v === preseleccion) opt.selected = true;
      select.appendChild(opt);
    });
  }

  async function cargarPais(pais, preRegion, preComuna) {
    try {
      regiones = await getJSON("/api/ubicaciones/" + encodeURIComponent(pais));
    } catch (e) {
      console.error("No se pudo cargar el catálogo de", pais, e);
      regiones = {};
    }
    repoblar(regionSelect, Object.keys(regiones), preRegion);
    repoblar(comunaSelect, regiones[regionSelect.value] || [], preComuna);
  }

  try {
    if (paisSelect) {
      const { paises } = await getJSON("/api/ubicaciones");
      repoblar(paisSelect, paises, paisActual);
    }
  } catch (e) {
    console.error("No se pudo cargar la lista de países", e);
    return;
  }

  if (paisSelect) {
    paisSelect.addEventListener("change", () => cargarPais(paisSelect.value, "", ""));
  }
  regionSelect.addEventListener("change", () =>
    repoblar(comunaSelect, regiones[regionSelect.value] || [], "")
  );

  await cargarPais(paisSelect ? paisSelect.value : "Chile", regionActual, comunaActual);
})();
