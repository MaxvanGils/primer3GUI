## Information

This folder contains all active versions of the P3G application, in addition to the required conda environment. 

Currently, there are two versions of the Streamlit app:

- P3G V1.0 - The Primer 3 code wrapped in a custom Streamlit run interface
- P3G V1.1 - Identical to version 1.0, but includes addition styling using custom CSS logic using Streamlit, but does have a potential security risk. ⚠️ 

V1.1 comes allows raw HTML/CSS to be rendered for additional or improved functionality and visual effects. While this enables advanced styling, it also carries potential security risks, including:

- HTML injection attacks – malicious HTML could be introduced if user input is ever incorporated.

- Cross-site scripting (XSS) – certain constructs could execute in the browser if not properly sanitized.

- Developer responsibility – Streamlit does not sandbox this HTML, so any unsafe content could compromise users. Streamlit does utilise strips tags automatically, reducing—but not eliminating—risk.


(also see [this](https://discuss.streamlit.io/t/why-is-using-html-unsafe/4863) discussion for further information about the risks)


### Local Development Safety

When running the app locally, these risks are minimal since the app is not exposed to the internet. However, caution is advised if you later deploy V1.1 to a network-accessible or public environment.

### Recommendation

V1.0 is fully functional and avoids any potential vulnerabilities.

Use V1.1 only for local experimentation or when you control all input sources and understand the risks.

In summary: V1.0 is safe and just as viable, while V1.1 adds additional styling at the cost of potential security concerns.