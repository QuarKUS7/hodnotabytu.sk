var ready = (callback) => {
    if (document.readyState != "loading") callback();
    else document.addEventListener("DOMContentLoaded", callback);
}
ready(() => {
    document.querySelector(".header").style.height = window.innerHeight / 1.5 + "px";
})


async function postFormDataAsJson({ url, formData }) {
    const plainFormData = Object.fromEntries(formData.entries());
    const formDataJsonString = JSON.stringify(plainFormData);

    const fetchOptions = {
        method: "POST",
        headers: {
            "Content-Type": "text/plain",
            Accept: "application/json",

        },
        body: formDataJsonString,
    };

    const response = await fetch(url, fetchOptions);

    if (!response.ok) {
        const errorMessage = await response.text();
        throw new Error(errorMessage);
    }

    return response.json();
}


async function handleFormSubmit(event) {
    event.preventDefault();

    const form = event.currentTarget;
    const url = form.action;

    try {
        const formData = new FormData(form);
        const responseData = await postFormDataAsJson({ url, formData });

        console.log({ responseData });
        var mainContainer = document.getElementById("myData");
        mainContainer.innerHTML = 'Aktuálna odhadovaná hodnota bytu je: ' + responseData.prediction.toLocaleString() + ' €.';
        var mainBox = document.getElementById("pred-box");
        mainBox.style.display = "";

    } catch (error) {
        console.error(error);
    }
}

const exampleForm = document.getElementById("byt-form");
exampleForm.addEventListener("submit", handleFormSubmit);
