Beautify Streamlit With Custom CSS
Introduction
Have you ever wanted to add custom CSS to your Streamlit dashboard? Well, let me show you how!

GitHub Repo: Click Here

If you haven’t installed Streamlit already, go ahead and open your terminal and run:

pip install streamlit
Now, create a new Python file and import Streamlit.

import streamlit as st
Let’s start by adding a title and then a button.

st.title("Custom CSS on Streamlit")
st.button(label = "Test Button")
Here is what the code currently produces.


Before Image of Streamlit App
Now that it is set up, you can add custom CSS in two ways.

Option 1 (Embedded CSS)
The first option lets you write your CSS code directly into your Python file. You can do this by using st.write(). Here is an example:

st.write(''' <style>
         
         /* Styles go here */
         
         </style>''', unsafe_allow_html=True)
Like any other CSS, we need to know what HTML element we are styling. Above, we created a button. So, let’s style the buttons with a box shadow.

st.write(''' <style>
         
          button {
            box-shadow: rgba(0, 0, 0, 0.25) 0px 54px 55px, rgba(0, 0, 0, 0.12) 0px -12px 30px, rgba(0, 0, 0, 0.12) 0px 4px 6px, rgba(0, 0, 0, 0.17) 0px 12px 13px, rgba(0, 0, 0, 0.09) 0px -3px 5px;
          }
         
         </style>''', unsafe_allow_html=True)
Here is the after photo of the Streamlit app:


After Photo of Streamlit App
Just like in normal CSS, you can use IDs, classes, etc. to style.

Keep in mind that you must put this at the top of your code under your imports. Additionally, you MUST set unsafe_allow_html to True.

Option 2 (External CSS File)
The second option is to add a separate CSS file in your directory. I recommend keeping this file in the parent directory (for simplicity), but you can put it wherever you like. I will be showing an example of it inside the parent folder.

Custom-CSS-Streamlit
  |
  - main.py
  - styles.css
Once created, return to your Python file and add the following line under your imports:

st.markdown('<style>' + open('styles.css').read() + '</style>', unsafe_allow_html=True)
Change “styles.css” to wherever you stored the CSS file. Now, add your CSS styles in the “styles.css” file. For example:

header {
    display: none !important;
}
Conclusion
And that’s all! If you need any help, leave a comment below and I will try to get back to you ASAP! Thank you for reading! If you’d like to see more tips on how to beautify Streamlit, check out my other articles here:

```
# Github example

import streamlit as st

# st.write(''' <style>
         
#           button {
#             box-shadow: rgba(0, 0, 0, 0.25) 0px 54px 55px, rgba(0, 0, 0, 0.12) 0px -12px 30px, rgba(0, 0, 0, 0.12) 0px 4px 6px, rgba(0, 0, 0, 0.17) 0px 12px 13px, rgba(0, 0, 0, 0.09) 0px -3px 5px;
#           }
         
#          </style>''', unsafe_allow_html=True)

st.markdown('<style>' + open('styles.css').read() + '</style>', unsafe_allow_html=True)

st.title("Custom CSS on Streamlit")
st.button(label = "Test Button")

```

```
/* CSS example */

header {
    display: none !important;
}
```
