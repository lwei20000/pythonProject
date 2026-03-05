const phoneInput = document.querySelector("#phone");
intlTelInput(phoneInput, {
    initialCountry: "auto",
    geoIpLookup: function(success, failure) {
        fetch('https://ipinfo.io/json', { cache: 'reload' })
            .then(response => response.json())
            .then(data => success(data.country))
            .catch(() => success('us'));
    },
    utilsScript: "https://cdnjs.cloudflare.com/ajax/libs/intl-tel-input/17.0.8/js/utils.js"
});