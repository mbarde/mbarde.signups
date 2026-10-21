# Additional form

The signup form always asks for prename, surname and email address. To ask
for more (for example a phone number, dietary requirements or a comment),
use an additional form built with
[collective.easyform](https://github.com/collective/collective.easyform):

1. Inside the signup sheet, add an `EasyForm`.
2. Define the fields in the form's _Define form fields_ view.
3. Publish the EasyForm.
4. Edit the signup sheet and select the form as _Additional form_.

The fields of the form are now shown in the signup form. The entered data is
stored with each signup, shown on the person's page and can be included in
emails with the `$$data$$` placeholder (see {doc}`emails`).

:::{important}
The EasyForm has to be published (or at least be viewable by everyone who
should be able to sign up). The signup sheet embeds the form, so visitors who
are not allowed to view the EasyForm can't open the signup sheet either -
they are asked to log in instead.
:::

:::{tip}
Exclude the EasyForm from navigation, so visitors don't open it on its own.
:::
