/* ============================================================================
   Boston in 3D.

   The city's own neighbourhood outlines, lifted off the ground into solid
   blocks, with every open issue standing on top of them as a pillar. Taller
   pillar = higher priority. Colour = which tier it falls in. Click one and it
   opens, same as clicking a row in the board.

   No tiles, no map service, no network — the shapes come from the same GeoJSON
   the flat map used, so this works on a dead wifi connection.
========================================================================== */

const M3 = (() => {
  // Boston sits around here. We flatten latitude/longitude onto a plane centred
  // on that point — over a city this small the distortion is invisible, and it
  // saves pulling in a projection library.
  const LAT0 = 42.3200, LON0 = -71.0900;
  const MPD = 111320;                     // metres per degree of latitude
  const UNIT = 120;                       // metres per world unit
  const kx = Math.cos(LAT0 * Math.PI / 180);

  const toXZ = (lat, lon) => [
    ((lon - LON0) * MPD * kx) / UNIT,
    -((lat - LAT0) * MPD) / UNIT,
  ];

  let scene, camera, renderer, controls, raycaster, pointer;
  let pillarGroup, groundGroup, pillars = [];
  let onPick = () => {};
  let hovered = null, container;

  function palette() {
    const cs = getComputedStyle(document.documentElement);
    const v = n => cs.getPropertyValue(n).trim();
    const light = document.documentElement.getAttribute("data-theme") === "light" ||
      (!document.documentElement.getAttribute("data-theme") &&
        matchMedia("(prefers-color-scheme:light)").matches);
    return {
      bg: light ? 0xE8EDF1 : 0x061119,
      land: light ? 0xC3D0DA : 0x123549,
      edge: light ? 0x8FA6B6 : 0x2C6E92,
      light,
    };
  }

  /* Turn one GeoJSON ring into a flat shape we can extrude upward. */
  function ringToShape(ring) {
    const shape = new THREE.Shape();
    ring.forEach(([lon, lat], i) => {
      const [x, z] = toXZ(lat, lon);
      i === 0 ? shape.moveTo(x, z) : shape.lineTo(x, z);
    });
    return shape;
  }

  function buildGround(hoods) {
    const P = palette();
    groundGroup.clear();
    const mat = new THREE.MeshLambertMaterial({ color: P.land });
    const edgeMat = new THREE.LineBasicMaterial({ color: P.edge, transparent: true, opacity: 0.85 });

    hoods.features.forEach(f => {
      const polys = f.geometry.type === "Polygon"
        ? [f.geometry.coordinates] : f.geometry.coordinates;
      polys.forEach(rings => {
        if (!rings[0] || rings[0].length < 4) return;
        const shape = ringToShape(rings[0]);
        // Inner rings are holes — ponds, the harbour cutting in.
        for (let i = 1; i < rings.length; i++) {
          if (rings[i].length >= 4) shape.holes.push(ringToShape(rings[i]));
        }
        const geo = new THREE.ExtrudeGeometry(shape, { depth: 1.2, bevelEnabled: false });
        geo.rotateX(-Math.PI / 2);
        const mesh = new THREE.Mesh(geo, mat);
        mesh.receiveShadow = true;
        groundGroup.add(mesh);

        // A crisp outline on top so neighbourhood borders stay readable.
        const pts = rings[0].map(([lon, lat]) => {
          const [x, z] = toXZ(lat, lon);
          return new THREE.Vector3(x, 1.22, z);
        });
        groundGroup.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), edgeMat));
      });
    });
  }

  /* One marker per issue, shaped like a map pin: a teardrop head floating on a
     hairline stem, over a soft ring painted on the ground. Height still carries
     priority — you can read the skyline — but the eye lands on the heads, which
     are the part that says what and where. */
  function buildPillars(items) {
    const P = palette();
    pillarGroup.clear();
    pillars = [];
    const maxScore = Math.max(...items.map(i => i.rank || i.sc || 1), 1);

    items.forEach(it => {
      if (!it.g) return;
      const [x, z] = toXZ(it.g[0], it.g[1]);
      const h = 6 + ((it.rank || it.sc || 0) / maxScore) * 30;
      const col = new THREE.Color(catColor(it.cat));
      const mk = { id: it.id, cat: it.cat, h };

      // Ground ring — where it is, and roughly how many people it touches.
      const rOuter = 1.8 + Math.min(Math.log(it.r + 1) * 0.9, 3.2);
      const ring = new THREE.Mesh(
        new THREE.RingGeometry(rOuter * 0.62, rOuter, 28),
        new THREE.MeshBasicMaterial({ color: col, transparent: true, opacity: P.light ? 0.4 : 0.5,
          side: THREE.DoubleSide, depthWrite: false })
      );
      ring.rotation.x = -Math.PI / 2;
      ring.position.set(x, 1.3, z);
      ring.userData = mk;
      pillarGroup.add(ring);

      // Hairline stem. Thin enough to read as a tether, not a column.
      const stem = new THREE.Mesh(
        new THREE.CylinderGeometry(0.11, 0.11, h, 6),
        new THREE.MeshBasicMaterial({ color: col, transparent: true,
          opacity: P.light ? 0.5 : 0.62, depthWrite: false })
      );
      stem.position.set(x, 1.3 + h / 2, z);
      stem.userData = mk;
      pillarGroup.add(stem);

      // The pin itself — cone pointing down into a rounded head.
      const head = new THREE.Group();
      const mat = new THREE.MeshLambertMaterial({
        color: col, emissive: col, emissiveIntensity: P.light ? 0.12 : 0.42 });
      const cone = new THREE.Mesh(new THREE.ConeGeometry(1.15, 2.3, 14), mat);
      cone.rotation.x = Math.PI;            // tip down, toward the street
      cone.position.y = 1.15;
      const ball = new THREE.Mesh(new THREE.SphereGeometry(1.18, 18, 14), mat);
      ball.position.y = 2.95;
      head.add(cone, ball);
      head.position.set(x, 1.3 + h, z);
      head.userData = mk;
      head.children.forEach(c => (c.userData = mk));
      pillarGroup.add(head);

      // A faint halo so heads stay findable when the camera pulls back.
      const halo = new THREE.Mesh(
        new THREE.SphereGeometry(2.1, 14, 12),
        new THREE.MeshBasicMaterial({ color: col, transparent: true,
          opacity: P.light ? 0.09 : 0.16, depthWrite: false })
      );
      halo.position.set(x, 1.3 + h + 2.95, z);
      halo.userData = mk;
      pillarGroup.add(halo);

      pillars.push(ring, stem, cone, ball, halo);
    });
  }

  function init(el, hoods, items, pick) {
    container = el;
    onPick = pick || (() => {});
    const P = palette();

    scene = new THREE.Scene();
    scene.background = new THREE.Color(P.bg);
    scene.fog = new THREE.Fog(P.bg, 180, 460);

    camera = new THREE.PerspectiveCamera(46, el.clientWidth / el.clientHeight, 0.5, 2000);
    camera.position.set(48, 92, 120);

    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    renderer.setSize(el.clientWidth, el.clientHeight);
    el.appendChild(renderer.domElement);

    scene.add(new THREE.AmbientLight(0xffffff, P.light ? 0.85 : 0.55));
    const key = new THREE.DirectionalLight(0xffffff, P.light ? 0.7 : 0.9);
    key.position.set(60, 140, 40);
    scene.add(key);
    const rim = new THREE.DirectionalLight(0x66aaff, 0.35);
    rim.position.set(-80, 60, -60);
    scene.add(rim);

    groundGroup = new THREE.Group();
    pillarGroup = new THREE.Group();
    scene.add(groundGroup, pillarGroup);

    buildGround(hoods);
    buildPillars(items);

    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.maxPolarAngle = Math.PI / 2.15;   // never let the camera go underground
    controls.minDistance = 30;
    controls.maxDistance = 320;
    controls.target.set(0, 0, 0);
    controls.autoRotate = true;
    controls.autoRotateSpeed = 0.35;

    raycaster = new THREE.Raycaster();
    pointer = new THREE.Vector2();

    renderer.domElement.addEventListener("pointermove", e => {
      const r = renderer.domElement.getBoundingClientRect();
      pointer.x = ((e.clientX - r.left) / r.width) * 2 - 1;
      pointer.y = -((e.clientY - r.top) / r.height) * 2 + 1;
    });
    // Any interaction stops the idle spin — it is an invitation, not a ride.
    renderer.domElement.addEventListener("pointerdown", () => { controls.autoRotate = false; });
    renderer.domElement.addEventListener("click", () => {
      raycaster.setFromCamera(pointer, camera);
      const hit = raycaster.intersectObjects(pillars, false)[0];
      if (hit) onPick(hit.object.userData.id);
    });

    new ResizeObserver(() => {
      if (!el.clientWidth) return;
      camera.aspect = el.clientWidth / el.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(el.clientWidth, el.clientHeight);
    }).observe(el);

    animate();
  }

  function animate() {
    requestAnimationFrame(animate);
    if (!renderer) return;
    controls.update();

    raycaster.setFromCamera(pointer, camera);
    const hit = raycaster.intersectObjects(pillars, false)[0];
    const id = hit ? hit.object.userData.id : null;
    if (id !== hovered) {
      hovered = id;
      renderer.domElement.style.cursor = id ? "pointer" : "grab";
      const P = palette();
      pillarGroup.children.forEach(m => {
        const on = m.userData && m.userData.id === hovered;
        const target = on ? 1.28 : 1;
        m.scale.setScalar(target);
        const apply = o => {
          if (!o.material) return;
          if (o.material.emissiveIntensity !== undefined)
            o.material.emissiveIntensity = on ? 0.95 : (P.light ? 0.12 : 0.42);
        };
        apply(m);
        if (m.children) m.children.forEach(apply);
      });
    }
    renderer.render(scene, camera);
  }

  /* Fly the camera to one pillar and make it pulse. */
  function focus(id) {
    const m = pillarGroup.children.find(c => c.userData && c.userData.id === id);
    if (!m || !controls) return;
    controls.autoRotate = false;
    const t = m.position.clone(); t.y = 0;
    controls.target.copy(t);
    const dir = new THREE.Vector3(0.4, 0.8, 0.9).normalize().multiplyScalar(58);
    camera.position.copy(t.clone().add(dir));
    controls.update();
  }

  const update = items => { if (pillarGroup) buildPillars(items); };
  const restyle = (hoods, items) => {
    if (!scene) return;
    const P = palette();
    scene.background = new THREE.Color(P.bg);
    scene.fog = new THREE.Fog(P.bg, 180, 460);
    buildGround(hoods); buildPillars(items);
  };

  return { init, update, focus, restyle };
})();
