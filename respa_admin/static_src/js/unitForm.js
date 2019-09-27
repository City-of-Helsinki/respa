
import {
  initializePeriods,
} from './periods';

import {
  toggleLanguage,
} from './resourceFormLanguage';


export function initializeUnitForm() {
  initializeEventHandlers();
  initializePeriods();
}

/*
* Attach all the event handlers to their objects upon load.
* */
function initializeEventHandlers() {
  enableLanguageButtons();
}

/*
* Bind event for hiding/showing translated fields in form.
* */
function enableLanguageButtons() {
  let languageSwitcher = document.getElementsByClassName('language-switcher');
  let languagesAmount = languageSwitcher[0].children.length;

  for (let i = 0; i < languagesAmount; i++) {
    let languageButton = languageSwitcher[0].children[i];
    let language = languageButton.value;
    languageButton.addEventListener('click', () => toggleLanguage(language), false);
  }
}

export function calendarHandler() {
  // Copied from bootstrap-datepicker@1.8.0/js/locales/bootstrap-datepicker.fi.js
  // As it can not be imported as a module, and would need to be shimmed
  $.fn.datepicker.dates['fi'] = {
		days: ["sunnuntai", "maanantai", "tiistai", "keskiviikko", "torstai", "perjantai", "lauantai"],
		daysShort: ["sun", "maa", "tii", "kes", "tor", "per", "lau"],
		daysMin: ["su", "ma", "ti", "ke", "to", "pe", "la"],
		months: ["tammikuu", "helmikuu", "maaliskuu", "huhtikuu", "toukokuu", "kesäkuu", "heinäkuu", "elokuu", "syyskuu", "lokakuu", "marraskuu", "joulukuu"],
		monthsShort: ["tam", "hel", "maa", "huh", "tou", "kes", "hei", "elo", "syy", "lok", "mar", "jou"],
		today: "tänään",
		clear: "Tyhjennä",
		weekStart: 1,
		format: "d.m.yyyy"
	};
}
