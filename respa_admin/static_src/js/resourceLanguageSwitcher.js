/*
* Toggle language based on the entered parameter.
* @param {String} language  Language provided by the DOM value.
* */
export function toggleLanguage(language) {
  let $languageInputs = $('[name$="_' + language + '"]');
  let $languageLabels = $('[for$="_' + language + '"]');
  $languageInputs.each((i, input) => input.classList.remove('hidden'));
  $languageLabels.each((i, input) => input.classList.remove('hidden'));

  let languagesToHide = getLanguagesToHide(language);
  languagesToHide.forEach(language => hideLanguage(language));
}

/*
* Hides the other languages from the user when loading the page,
* leaving the correct language visible based on the user's language setting.
*
* If the language is not recognized it will fall back to Finnish.
* */
export function toggleStartupLanguage() {
  let languages = getAllLanguages();
  let currentLanguage = getCurrentLanguage();
  let languagesToHide = getLanguagesToHide(currentLanguage);

  if (!languages.includes(currentLanguage)) {
    currentLanguage = 'fi'; //Finnish is the fallback language.
  }

  languagesToHide.forEach(language => hideLanguage(language));
}

/*
* Hides all inputs where the name postfix is _{language},
* ex; name_en, name_fi or name_sv.
*
* Hides the labels for these inputs as well.
* */
function hideLanguage(language) {
  let $languageInputs = $('[name$="_' + language + '"]');
  let $languageLabels = $('[for$="_' + language + '"]');
  $languageInputs.each((i, input) => input.classList.add('hidden'));
  $languageLabels.each((i, input) => input.classList.add('hidden'));
}

/*
* Returns string value of User's current
* browser language setting.
*
* Ex; 'fi', 'sv' or 'en' etc.
* */
function getCurrentLanguage() {
  return document.documentElement.lang;
}

/*
* Helper function for getting languages to hide
* based on the the current languages list.
* */
function getLanguagesToHide(currentLanguage) {
  let languages = getAllLanguages();
  return languages.filter(language => {return currentLanguage !== language});
}

/*
* All current languages are served from django's settings.
* */
function getAllLanguages() {
  let allLanguages = $('#all-languages').children();
  let languages = [];

  allLanguages.each((i, input) => languages.push(input.value));

  return languages;
}
