
// Log when extension starts
console.log("Proxy Auth Extension loaded");
console.log("Protocol: socks5");
console.log("Proxy: 45.32.122.119:10103");
console.log("Username: proxy104");

// Only handle proxy authentication when requested
function callbackFn(details) {
    console.log("Proxy auth requested for:", details.url);
    return {
        authCredentials: {
            username: "proxy104",
            password: "123"
        }
    };
}

chrome.webRequest.onAuthRequired.addListener(
    callbackFn,
    {urls: ["<all_urls>"]},
    ['blocking']
);
