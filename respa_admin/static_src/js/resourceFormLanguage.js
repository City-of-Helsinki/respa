/*
* Toggle language based on entered language for all fields in the
* whole form.
*
* @param {String} language  Language provided by the DOM value.
* */
export function toggleLanguage(language) {
  let $languageInputs = $('[name$="_' + language + '"]');
  let $languageLabels = $('[for$="_' + language + '"]');
  let $languageButtons = $('[name$="language-' + language + '"]');

  $languageInputs.each(
    (i, input) =>
      (input.classList.contains('hidden')) ? input.classList.remove('hidden') : input.classList.add('hidden')
  );

  $languageLabels.each(
    (i, input) =>
      (input.classList.contains('hidden')) ? input.classList.remove('hidden') : input.classList.add('hidden')
  );

  $languageButtons.each(
    (i, input) =>
      (input.classList.contains('language-item-selected')) ? input.classList.remove('language-item-selected') : input.classList.add('language-item-selected')
  );
}

/*
* Hides the other languages from the user when loading the page,
* leaving the correct language visible based on the user's language setting.
*
* @param language {String}    If not provided => current language will be chosen.
* @param input {DOM Object}   If provided, all other than current language will be hidden
*                             from the DOM in input DOM element of choice.
* */
export function toggleCurrentLanguage(language = undefined, input = null) {
  if (language === undefined) { language = getCurrentLanguage(); }
  let languagesToHide = getLanguagesToHide(language);
  languagesToHide.forEach(language => hideLanguage(language, input));
  let $languageButtons = $('[name$="language-' + language + '"]');
  $languageButtons.each((i, input) => input.classList.add('language-item-selected'));
}

/*
* Reduce the amount of fields translated by the user
* from the current number displayed in the language buttons.
*
* The initial value is served from the backend.
* */
export function calculateTranslatedFields() {
  for (const language of getAllLanguages()) {
    const $languageInputs = $('[name$="_' + language + '"]');
    let languageCount = 0; //

    for (const languageInput of $languageInputs) {
      if (languageInput.value) {
        languageCount++;
      }
    }

    const $languageButton = $('[name="language-' + language + '"]');
    const currentCountForLanguage = $languageButton.find('span').text();
    const UNICODE_CHECKMARK = '\u2713'
    if(currentCountForLanguage - languageCount === 0) {
      $languageButton.find('span').css('background-color', '#23a000').text(UNICODE_CHECKMARK);
    }
    else {
      $languageButton.find('span').text(currentCountForLanguage - languageCount);
    }
  }
}

/*
* Hides all inputs where the name postfix is _{language},
* ex; name_en, name_fi or name_sv.
*
* Hides the labels for these inputs as well.
* */
function hideLanguage(language, input = null) {
  let $languageInputs = null;
  let $languageLabels = null;
  if (input) {
    $languageInputs = $(input).find('[name$="_' + language + '"]');
    $languageLabels = $(input).find('[for$="_' + language + '"]');
  } else {
    $languageInputs = $('[name$="_' + language + '"]');
    $languageLabels = $('[for$="_' + language + '"]');
  }

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
  let languages = getAllLanguages();
  let currentLanguage = document.documentElement.lang;

  if (!languages.includes(currentLanguage)) {
    currentLanguage = 'fi'; //Finnish is the fallback language.
  }

  return currentLanguage;
}

/*
* Helper function for getting languages to hide
* based on the the current language.
* */
function getLanguagesToHide(currentLanguage) {
  const languages = getAllLanguages();
  return languages.filter((language) => (language !== currentLanguage));
}

/*
* All current languages are served from django's settings.
* */
function getAllLanguages() {
  let allLanguages = $('#all-languages').children();
  let languages = [];
  allLanguages.each((i, domLanguage) => languages.push(domLanguage.value));

  return languages;
}
