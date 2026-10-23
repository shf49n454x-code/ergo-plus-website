/* ERGO-PLUS – gemeinsames Skript aller Seiten.
   Menü, Cookie-Hinweis mit GA4, Weiterleitung alter Sprungmarken, Kontaktformular.
   Wird per defer geladen; die Adresse stempelt tools/seiten/bauen.py. */
(function () {
  'use strict';

  // ── Alte Sprungmarken des Onepagers auf die neuen Seiten umlenken ──
  // Links in Mails, Google-Snippets und Lesezeichen zeigen noch auf /#contact usw.
  var alt = {
    '#contact': '/kontakt.html', '#kontakt': '/kontakt.html',
    '#products': '/sitzloesungen.html', '#tech': '/sitzloesungen.html#technik',
    '#steps': '/ablauf-und-kosten.html', '#team': '/ueber-ergo-plus.html#team',
    '#about': '/ueber-ergo-plus.html', '#blog': '/blog/',
    '#conditions': '/krankheitsbilder.html', '#anwender': '/krankheitsbilder.html'
  };
  if ((location.pathname === '/' || location.pathname === '/index.html') && alt[location.hash]) {
    location.replace(alt[location.hash]);
    return;
  }

  // ── Menü auf schmalen Bildschirmen ──
  var burger = document.querySelector('.burger');
  var menue = document.getElementById('site-nav');
  if (burger && menue) {
    var setzen = function (offen) {
      burger.setAttribute('aria-expanded', String(offen));
      burger.setAttribute('aria-label', offen ? 'Menü schließen' : 'Menü öffnen');
      menue.classList.toggle('open', offen);
      document.body.style.overflow = offen ? 'hidden' : '';
    };
    burger.addEventListener('click', function () {
      setzen(burger.getAttribute('aria-expanded') !== 'true');
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && menue.classList.contains('open')) { setzen(false); burger.focus(); }
    });
    menue.querySelectorAll('a').forEach(function (a) {
      a.addEventListener('click', function () { setzen(false); });
    });
  }

  var ruhig = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ── Startseite: Kopfzeile oben transparent, über der Bühne dunkel, danach weiß ──
  var kopf = document.querySelector('.start .site-head');
  var buehne = document.querySelector('.buehne');
  if (kopf && buehne) {
    var kopfSetzen = function () {
      var hinterBuehne = buehne.getBoundingClientRect().bottom <= kopf.offsetHeight;
      kopf.classList.toggle('ist-fest', hinterBuehne);
      kopf.classList.toggle('ist-dunkel', !hinterBuehne && window.scrollY > 24);
    };
    kopfSetzen();
    window.addEventListener('scroll', kopfSetzen, { passive: true });
    window.addEventListener('resize', kopfSetzen);
  }

  // ── Bühne: das Maß hervorheben, dessen Text gerade gelesen wird ──
  var figur = buehne && buehne.querySelector('.measure-fig');
  if (figur && 'IntersectionObserver' in window) {
    // Erst nach dem Einzeichnen dimmen, sonst hält die Animation die Deckkraft fest
    var letztes = figur.querySelector('.ml-tag--tiefe');
    var bereit = function () { figur.classList.add('ist-bereit'); };
    if (ruhig || !letztes) bereit(); else { letztes.addEventListener('animationend', bereit, { once: true }); setTimeout(bereit, 2500); }
    buehne.classList.add('ist-interaktiv');
    var schritte = buehne.querySelectorAll('.buehne__schritt');
    var beobachter;
    var beobachten = function () {
      if (beobachter) beobachter.disconnect();
      // Aktiv ist der Schritt, der eine schmale Lesezeile kreuzt. Auf dem Handy liegt
      // sie knapp unter der festen Figur, am Rechner in der Bildschirmmitte.
      var h = window.innerHeight;
      var hulle = buehne.querySelector('.buehne__fig');
      var klebt = hulle && getComputedStyle(hulle).position === 'sticky' && window.innerWidth < 960;
      var zeile = klebt ? Math.min(h - 40, hulle.getBoundingClientRect().height + 76 + 60) : h * 0.5;
      beobachter = new IntersectionObserver(function (eintraege) {
        eintraege.forEach(function (e) {
          e.target.classList.toggle('ist-aktiv', e.isIntersecting);
          if (e.isIntersecting) figur.setAttribute('data-aktiv', e.target.getAttribute('data-mass'));
        });
        if (!buehne.querySelector('.buehne__schritt.ist-aktiv')) figur.setAttribute('data-aktiv', '');
      }, { rootMargin: '-' + Math.round(zeile) + 'px 0px -' + Math.round(h - zeile - 8) + 'px 0px' });
      schritte.forEach(function (el) { beobachter.observe(el); });
    };
    beobachten();
    window.addEventListener('resize', beobachten);
  }

  // ── Galerie: Pfeile blättern um eine Kachel ──
  var liste = document.getElementById('galerie-liste');
  if (liste) {
    var knoepfe = document.querySelectorAll('.galerie__btn');
    var schritt = function () { var i = liste.querySelector('.galerie__item'); return i ? i.getBoundingClientRect().width + 24 : 400; };
    var zustand = function () {
      var max = liste.scrollWidth - liste.clientWidth - 4;
      knoepfe.forEach(function (k) {
        k.disabled = k.getAttribute('data-richtung') === '-1' ? liste.scrollLeft <= 4 : liste.scrollLeft >= max;
      });
    };
    knoepfe.forEach(function (k) {
      k.addEventListener('click', function () {
        liste.scrollBy({ left: schritt() * Number(k.getAttribute('data-richtung')), behavior: ruhig ? 'auto' : 'smooth' });
      });
    });
    liste.addEventListener('scroll', zustand, { passive: true });
    window.addEventListener('resize', zustand);
    zustand();
  }

  // ── Cookie-Hinweis und Google Analytics (erst nach Zustimmung) ──
  var GA4_ID = 'G-Y8T7VW3V73';
  var lesen = function () { try { return localStorage.getItem('ep-cookies'); } catch (e) { return null; } };
  var schreiben = function (v) { try { v === null ? localStorage.removeItem('ep-cookies') : localStorage.setItem('ep-cookies', v); } catch (e) {} };
  function ladeGA4() {
    if (window.gtag) return;
    var t = document.createElement('script');
    t.async = true;
    t.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA4_ID;
    document.head.appendChild(t);
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag('js', new Date());
    window.gtag('config', GA4_ID, { anonymize_ip: true });
  }
  if (lesen() === 'all') ladeGA4();

  var banner = document.getElementById('cookie-banner');
  if (banner) {
    if (!lesen()) setTimeout(function () { banner.classList.add('visible'); }, 800);
    var schliessen = function (v) {
      schreiben(v);
      banner.classList.remove('visible');
      if (v === 'all') ladeGA4();
    };
    var b1 = document.getElementById('cookie-accept');
    var b2 = document.getElementById('cookie-essential');
    var b3 = document.getElementById('cookie-settings-link');
    if (b1) b1.addEventListener('click', function () { schliessen('all'); });
    if (b2) b2.addEventListener('click', function () { schliessen('essential'); });
    if (b3) b3.addEventListener('click', function (e) {
      e.preventDefault();
      schreiben(null);
      banner.classList.add('visible');
      if (b2) b2.focus();
    });
  }

  // ── Kontaktformular (nur auf /kontakt.html) ──
  var form = document.getElementById('contact-form');
  if (!form) return;
  var success = document.getElementById('form-success');
  var erfolgstext = document.getElementById('form-success-text');
  var btn = document.getElementById('btn-submit');
  var ts = document.getElementById('f-ts');

  // Ladezeitpunkt setzen. Wer das Formular in unter drei Sekunden
  // abschickt, hat es nicht gelesen – der Server weist das ab.
  if (ts) ts.value = String(Date.now());
  var beschriftung = btn ? btn.innerHTML : '';

  // Vorauswahl aus der Adresse: /kontakt.html?thema=mfs
  var thema = new URLSearchParams(location.search).get('thema');
  var auswahl = document.getElementById('f-product');
  if (thema && auswahl) {
    for (var i = 0; i < auswahl.options.length; i++) {
      if (auswahl.options[i].dataset.thema === thema) auswahl.selectedIndex = i;
    }
  }

  function fehlerZeigen(htmlText) {
    var box = form.querySelector('.form-fehler');
    if (!box) {
      box = document.createElement('div');
      box.className = 'form-fehler';
      box.setAttribute('role', 'alert');
      form.appendChild(box);
    }
    box.innerHTML = htmlText;
    box.scrollIntoView({ behavior: ruhig ? 'auto' : 'smooth', block: 'center' });
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var pflicht = ['f-first', 'f-last', 'f-email'].map(function (id) { return document.getElementById(id); });
    var gueltig = true;
    pflicht.forEach(function (el) {
      var leer = !el.value.trim();
      el.setAttribute('aria-invalid', String(leer));
      if (leer) gueltig = false;
    });
    var email = pflicht[2];
    if (email.value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value)) {
      email.setAttribute('aria-invalid', 'true');
      gueltig = false;
    }
    if (!gueltig) {
      fehlerZeigen('Bitte füllen Sie Vorname, Nachname und eine gültige E-Mail-Adresse aus.');
      return;
    }
    var alteBox = form.querySelector('.form-fehler');
    if (alteBox) alteBox.remove();
    if (btn) { btn.disabled = true; btn.textContent = 'Wird gesendet …'; }

    fetch('/kontakt.php', {
      method: 'POST',
      // urlencoded statt multipart: der Server weist multipart an PHP ab (PHP2Shell-Abwehr, .htaccess)
      body: new URLSearchParams(new FormData(form)),
      headers: { 'Accept': 'application/json' }
    })
      .then(function (r) { return r.json(); })
      .then(function (daten) {
        if (daten.ok) {
          if (erfolgstext && daten.meldung) erfolgstext.textContent = daten.meldung;
          form.hidden = true;
          success.classList.add('show');
          success.focus();
          return;
        }
        var eigen = new Error(String(daten.meldung || 'Das Absenden hat nicht geklappt.').trim());
        eigen.eigeneMeldung = true;
        throw eigen;
      })
      .catch(function (fehler) {
        // Kein stiller Erfolg: sagen, dass es nicht geklappt hat, und sofort
        // einen Weg nennen, der funktioniert. Nur eigene, deutsche Servermeldungen zeigen.
        var text = fehler && fehler.eigeneMeldung ? fehler.message : 'Das Absenden hat nicht geklappt.';
        // Der Server hängt teils selbst „Bitte rufen Sie uns an …“ an. Das schneiden wir ab
        // und setzen den Satz einheitlich, mit antippbarer Nummer.
        text = text.replace(/\s*Bitte rufen Sie uns an.*$/i, '').replace(/([^.!?])$/, '$1.');
        var span = document.createElement('span');
        span.textContent = text;
        fehlerZeigen(span.innerHTML + ' Bitte rufen Sie uns an: <a class="nobr" href="tel:+49602112807">06021 12807</a>. ' +
          'Oder schreiben Sie an <a href="mailto:info@ergo-plus.de">info@ergo-plus.de</a>.');
      })
      .finally(function () {
        if (btn) { btn.disabled = false; btn.innerHTML = beschriftung; }
      });
  });
})();
