
"""
Tests for L{xmantissa.liveform}.
"""

from xml.dom.minidom import parseString

from zope.interface import implements
from zope.interface.verify import verifyObject

from twisted.internet.defer import Deferred
from twisted.trial.unittest import TestCase

from epsilon.hotfix import require
require('twisted', 'trial_assertwarns')

from nevow.page import renderer
from nevow.tags import directive, div, span
from nevow.loaders import stan
from nevow.flat import flatten
from nevow.inevow import IQ
from nevow.athena import expose

from xmantissa.liveform import (
    FORM_INPUT, TEXT_INPUT, PASSWORD_INPUT, CHOICE_INPUT, Parameter,
    TextParameterView, PasswordParameterView, ChoiceParameter,
    ChoiceParameterView, Option, OptionView, LiveForm, ListParameter,
    ListChangeParameterView, ListChangeParameter,
    RepeatedLiveFormWrapper, _LIVEFORM_JS_CLASS, _SUBFORM_JS_CLASS, EditObject,
    FormParameter, FormParameterView, FormInputParameterView)

from xmantissa.webtheme import getLoader
from xmantissa.test.rendertools import TagTestingMixin, renderLiveFragment
from xmantissa.ixmantissa import IParameter, IParameterView


class StubView(object):
    """
    Behaviorless implementation of L{IParameterView} used where such an object
    is required by tests.
    """
    implements(IParameterView)

    patternName = 'text'

    def setDefaultTemplate(self, tag):
        """
        Ignore the default template tag.
        """



class ParameterTestsMixin:
    """
    Mixin defining various tests common to different parameter view objects.
    """
    def viewFactory(self, parameter):
        """
        Instantiate a view object for the given parameter.
        """
        raise NotImplementedError("%s did not implement viewFactory")


    def test_fromInputs(self):
        """
        The parameter should provide a C{fromInputs} method for LiveForm to poke.
        """
        self.assertTrue(
            hasattr(self.param, 'fromInputs'),
            "Parameter did not even have fromInputs method, let alone "
            "implement it correctly.  Override this test method and "
            "assert something meaningful.")


    def test_comparison(self):
        """
        Parameter view objects should compare equal to other view objects of
        the same type which wrap the same underlying parameter object.
        """
        self.assertTrue(self.viewFactory(self.param) == self.viewFactory(self.param))
        self.assertFalse(self.viewFactory(self.param) != self.viewFactory(self.param))
        self.assertFalse(self.viewFactory(self.param) == object())
        self.assertTrue(self.viewFactory(self.param) != object())


    def test_name(self):
        """
        The I{name} renderer of the view object should render the name of the
        L{Parameter} it wraps as a child of the tag it is given.
        """
        tag = div()
        renderedName = renderer.get(self.view, 'name')(None, tag)
        self.assertTag(tag, 'div', {}, [self.name])


    def test_label(self):
        """
        The I{label} renderer of the view object should render the label of
        the L{Parameter} it wraps as a child of the tag it is given.
        """
        tag = div()
        renderedLabel = renderer.get(self.view, 'label')(None, tag)
        self.assertTag(tag, 'div', {}, [self.label])


    def test_withoutLabel(self):
        """
        The I{label} renderer of the view object should do nothing if the
        wrapped L{Parameter} has no label.
        """
        tag = div()
        self.param.label = None
        renderedOptions = renderer.get(self.view, 'label')(None, tag)
        self.assertTag(renderedOptions, 'div', {}, [])


    def _defaultRenderTest(self, fragmentName):
        loader = getLoader(fragmentName)
        document = loader.load()
        patternName = self.view.patternName + '-input-container'
        pattern = IQ(document).onePattern(patternName)
        self.view.setDefaultTemplate(pattern)
        html = flatten(self.view)

        # If it parses, well, that's the best we can do, given an arbitrary
        # template.
        document = parseString(html)


    def test_renderWithDefault(self):
        """
        The parameter view should be renderable using the default template.
        """
        return self._defaultRenderTest('liveform')


    def test_renderWithCompact(self):
        """
        The parameter view should be renderable using the compact template.
        """
        return self._defaultRenderTest('liveform-compact')


    def test_clone(self):
        """
        The parameter should be cloneable.
        """
        newDefault = object()
        param = self.param.clone(newDefault)
        self.assertTrue(isinstance(param, self.param.__class__))
        self.assertIdentical(param.name, self.param.name)
        self.assertIdentical(param.label, self.param.label)
        self.assertIdentical(param.description, self.param.description)
        self.assertIdentical(param.coercer, self.param.coercer)
        self.assertIdentical(param.default, newDefault)
        self.assertIdentical(param.viewFactory, self.param.viewFactory)



class TextLikeParameterViewTestsMixin:
    """
    Mixin defining tests for parameter views which are simple text fields.
    """
    def type():
        def get(self):
            raise AttributeError("%s did not define the type attribute")
        return get,
    type = property(*type())

    name = u'param name'
    label = u'param label'
    coercer = lambda value: value
    description = u'param desc'
    default = u'param default value'


    def setUp(self):
        """
        Create a L{Parameter} and a L{TextParameterView} wrapped around it.
        """
        self.param = Parameter(
            self.name, self.type, self.coercer, self.label, self.description,
            self.default)
        self.view = self.viewFactory(self.param)


    def test_default(self):
        """
        L{TextParameterView.value} should render the default value of the
        L{Parameter} it wraps as a child of the tag it is given.
        """
        tag = div()
        renderedDefault = renderer.get(self.view, 'default')(None, tag)
        self.assertTag(tag, 'div', {}, [self.default])


    def test_withoutDefault(self):
        """
        L{TextParameterView.value} should leave the tag it is given unchanged
        if the L{Parameter} it wraps has a C{None} default.
        """
        tag = div()
        self.param.default = None
        renderedDefault = renderer.get(self.view, 'default')(None, tag)
        self.assertTag(tag, 'div', {}, [])


    def test_description(self):
        """
        L{TextParameterView.description} should render the description of the
        L{Parameter} it wraps as a child of the tag it is given.
        """
        tag = div()
        renderedDescription = renderer.get(self.view, 'description')(None, tag)
        self.assertTag(tag, 'div', {}, [self.description])


    def test_withoutDescription(self):
        """
        L{TextParameterView.description} should leave the tag it is given
        unchanged if the L{Parameter} it wraps has no description.
        """
        tag = div()
        self.param.description = None
        renderedDescription = renderer.get(self.view, 'description')(None, tag)
        self.assertTag(tag, 'div', {}, [])


    def test_renderCompletely(self):
        """
        L{TextParameterView} should be renderable in the usual Nevow manner.
        """
        self.view.docFactory = stan(div[
                div(render=directive('name')),
                div(render=directive('label')),
                div(render=directive('default')),
                div(render=directive('description'))])
        html = flatten(self.view)
        self.assertEqual(
            html,
            '<div><div>param name</div><div>param label</div>'
            '<div>param default value</div><div>param desc</div></div>')



class TextParameterViewTests(TextLikeParameterViewTestsMixin,
                             TestCase, ParameterTestsMixin,
                             TagTestingMixin):
    """
    Tests for the view generation code for C{TEXT_INPUT} L{Parameter}
    instances.
    """
    type = TEXT_INPUT
    viewFactory = TextParameterView



class PasswordParameterViewTests(TextLikeParameterViewTestsMixin,
                                 TestCase, ParameterTestsMixin,
                                 TagTestingMixin):
    """
    Tests for the view generation code for C{PASSWORD_INPUT} L{Parameter}
    instances.
    """
    type = PASSWORD_INPUT
    viewFactory = PasswordParameterView



class ChoiceParameterTests(TestCase, ParameterTestsMixin, TagTestingMixin):
    """
    Tests for the view generation code for C{CHOICE_INPUT} L{Parameter}
    instances.
    """
    viewFactory = ChoiceParameterView

    def setUp(self):
        """
        Create a L{Parameter} and a L{ChoiceParameterView} wrapped around it.
        """
        self.type = CHOICE_INPUT
        self.name = u'choice name'
        self.choices = [
            Option(u'description one', u'value one', False),
            Option(u'description two', u'value two', False)]
        self.label = u'choice label'
        self.description = u'choice description'
        self.multiple = False
        self.param = ChoiceParameter(
            self.name, self.choices, self.label, self.description,
            self.multiple)
        self.view = self.viewFactory(self.param)


    def test_multiple(self):
        """
        L{ChoiceParameterView.multiple} should render the multiple attribute on
        the tag it is passed if the wrapped L{ChoiceParameter} is a
        L{MULTI_CHOICE_INPUT}.
        """
        tag = div()
        self.param.multiple = True
        renderedSelect = renderer.get(self.view, 'multiple')(None, tag)
        self.assertTag(tag, 'div', {'multiple': 'multiple'}, [])


    def test_fromInputs(self):
        """
        L{ChoiceParameter.fromInputs} should extract the inputs directed at it
        and pass them on to the coerce function.
        """
        self.assertEqual(
            self.param.fromInputs({self.name: ['0']}),
            self.choices[0].value)


    def test_single(self):
        """
        L{ChoiceParameterView.multiple} should not render the multiple
        attribute on the tag it is passed if the wrapped L{ChoiceParameter} is
        a L{CHOICE_INPUT}.
        """
        tag = div()
        renderedSelect = renderer.get(self.view, 'multiple')(None, tag)
        self.assertTag(tag, 'div', {}, [])


    def test_options(self):
        """
        L{ChoiceParameterView.options} should load the I{option} pattern from
        the tag it is passed and add copies of it as children to the tag for
        all of the options passed to L{ChoiceParameterView.__init__}.
        """
        option = span(pattern='option')
        tag = div[option]
        renderedOptions = renderer.get(self.view, 'options')(None, tag)
        self.assertEqual(
            renderedOptions.children[1:],
            [OptionView(index, c, None)
             for (index, c)
             in enumerate(self.choices)])


    def test_description(self):
        """
        L{ChoiceParameterView.description} should add the description of the
        wrapped L{ChoiceParameter} to the tag it is passed.
        """
        tag = div()
        renderedOptions = renderer.get(self.view, 'description')(None, tag)
        self.assertTag(renderedOptions, 'div', {}, [self.description])


    def test_withoutDescription(self):
        """
        L{ChoiceParameterView.description} should do nothing if the wrapped
        L{ChoiceParameter} has no description.
        """
        tag = div()
        self.param.description = None
        renderedOptions = renderer.get(self.view, 'description')(None, tag)
        self.assertTag(renderedOptions, 'div', {}, [])


    def test_clone(self):
        """
        L{ChoiceParameter} instances should be cloneable.
        """
        newChoices = [object()]
        param = self.param.clone(newChoices)
        self.assertTrue(isinstance(param, self.param.__class__))
        self.assertIdentical(param.name, self.param.name)
        self.assertIdentical(param.label, self.param.label)
        self.assertIdentical(param.type, self.param.type)
        self.assertIdentical(param.description, self.param.description)
        self.assertIdentical(param.multiple, self.param.multiple)
        self.assertIdentical(param.choices, newChoices)
        self.assertIdentical(param.viewFactory, self.param.viewFactory)



class OptionTests(TestCase, TagTestingMixin):
    """
    Tests for the view generation code for a single choice, L{OptionView}.
    """
    simpleOptionTag = div[
            div(render=directive('description')),
            div(render=directive('value')),
            div(render=directive('index')),
            div(render=directive('selected'))]

    def setUp(self):
        """
        Create an L{Option} and an L{OptionView} wrapped around it.
        """
        self.description = u'option description'
        self.value = u'option value'
        self.selected = True
        self.option = Option(self.description, self.value, self.selected)
        self.index = 3
        self.view = OptionView(self.index, self.option, self.simpleOptionTag)


    def test_description(self):
        """
        L{OptionView.description} should add the description of the option it
        wraps as a child to the tag it is passed.
        """
        tag = div()
        renderedDescription = renderer.get(self.view, 'description')(None, tag)
        self.assertTag(renderedDescription, 'div', {}, [self.description])


    def test_value(self):
        """
        L{OptionView.value} should add the value of the option it wraps as a
        child to the tag it is passed.
        """
        tag = div()
        renderedValue = renderer.get(self.view, 'value')(None, tag)
        self.assertTag(renderedValue, 'div', {}, [self.value])


    def test_index(self):
        """
        L{OptionView.index} should add the index passed to
        L{OptionView.__init__} to the tag it is passed.
        """
        tag = div()
        renderedIndex = renderer.get(self.view, 'index')(None, tag)
        self.assertTag(renderedIndex, 'div', {}, [self.index])


    def test_selected(self):
        """
        L{OptionView.selected} should add a I{selected} attribute to the tag it
        is passed if the option it wraps is selected.
        """
        tag = div()
        renderedValue = renderer.get(self.view, 'selected')(None, tag)
        self.assertTag(renderedValue, 'div', {'selected': 'selected'}, [])


    def test_notSelected(self):
        """
        L{OptionView.selected} should not add a I{selected} attribute to the
        tag it is passed if the option it wraps is not selected.
        """
        self.option.selected = False
        tag = div()
        renderedValue = renderer.get(self.view, 'selected')(None, tag)
        self.assertTag(renderedValue, 'div', {}, [])


    def test_renderCompletely(self):
        """
        L{ChoiceParameterView} should be renderable in the usual Nevow manner.
        """
        html = flatten(self.view)
        self.assertEqual(
            html,
            '<div><div>option description</div><div>option value</div>'
            '<div>3</div><div selected="selected"></div></div>')



class ListParameterTests(TestCase):
    """
    Tests for L{ListParameter}.
    """
    def test_fromInputs(self):
        """
        L{ListParameter.fromInputs} should extract multiple values from the
        mapping it is passed and coerce each value, returning a Deferred which
        fires with a list of all of the coerced values.
        """
        name = u'list param'
        param = ListParameter(name, int, 2)
        result = param.fromInputs({name + u'_0': [u'1'],
                                   name + u'_1': [u'3']})
        result.addCallback(self.assertEqual, [1, 3])
        return result



class FormParameterTests(TestCase):
    """
    Tests for L{Parameter} created with a type of L{FORM_INPUT} and for
    L{FormParameter}.
    """
    def test_deprecated(self):
        """
        Creating a L{Parameter} with a type of L{FORM_INPUT} should emit a
        deprecation warning referring to L{FormParameter}.
        """
        self.assertWarns(
            DeprecationWarning,
            "Create a FormParameter, not a Parameter with type FORM_INPUT",
            __file__,
            lambda: Parameter(None, FORM_INPUT, None))


    def test_viewFactory(self):
        """
        L{FormParameter.viewFactory} should return a L{FormParameterView}
        wrapped around the parameter.
        """
        parameter = FormParameter(lambda **kw: None, LiveForm(None, []))
        view = parameter.viewFactory(parameter, None)
        self.assertTrue(isinstance(view, FormParameterView))
        self.assertIdentical(view.parameter, parameter)


    def test_provides(self):
        """
        L{FormParameter} should provide L{IParameter}.
        """
        parameter = FormParameter(u'name', None)
        self.assertTrue(IParameter.providedBy(parameter))
        self.assertTrue(verifyObject(IParameter, parameter))


    def test_fromInputs(self):
        """
        L{FormParameter.fromInputs} should extract the input value which
        corresponds to the parameter's name and pass it to the invoke method of
        the wrapped form.
        """
        value = '-13'
        invoked = {}
        param = u'foo'
        form = LiveForm(invoked.update, [Parameter(param, TEXT_INPUT, int)])
        name = u'name'
        parameter = FormParameter(name, form)
        parameter.fromInputs({name: [{param: [value]}]})
        self.assertEqual(invoked, {param: int(value)})


    def test_compact(self):
        """
        L{FormParameter.compact} should call compact on the wrapped form.
        """
        class FakeForm(object):
            isCompact = False
            def compact(self):
                self.isCompact = True

        form = FakeForm()
        parameter = FormParameter(None, form)
        parameter.compact()
        self.assertTrue(form.isCompact)



class FormParameterViewTests(TestCase):
    """
    Tests for L{FormParameterView}.
    """
    def test_provides(self):
        """
        L{FormParameterView} should provide L{IParameterView}.
        """
        self.assertTrue(IParameterView.providedBy(FormParameterView(None)))


    def test_inputs(self):
        """
        The I{input} renderer of L{FormParameterView} should add a subform from
        its wrapped form as a child to the tag it is called with.
        """
        form = LiveForm(None, [])
        name = u'bar'
        parameter = FormParameter(name, form)
        view = FormParameterView(parameter)
        tag = div()
        inputRenderer = renderer.get(view, 'input')
        tag = inputRenderer(None, div())
        self.assertEqual(tag.tagName, 'div')
        self.assertEqual(tag.attributes, {})
        self.assertEqual(tag.children, [form])
        self.assertIdentical(form.fragmentParent, view)
        self.assertEqual(form.subFormName, name)



class FormInputParameterViewTests(TestCase):
    """
    Tests for deprecated L{FormInputParameterView}.
    """
    def test_inputs(self):
        """
        The I{input} renderer of L{FormParameterView} should add a subform from
        its wrapped form as a child to the tag it is called with.
        """
        form = LiveForm(None, [])

        name = u'bar'
        type = FORM_INPUT
        form = LiveForm(None, [])
        parameter = Parameter(name, type, form)
        view = FormInputParameterView(parameter)
        tag = div()
        inputRenderer = renderer.get(view, 'input')
        tag = inputRenderer(None, div())
        self.assertEqual(tag.tagName, 'div')
        self.assertEqual(tag.attributes, {})
        self.assertEqual(tag.children, [form])
        self.assertIdentical(form.fragmentParent, view)
        self.assertEqual(form.subFormName, name)


class LiveFormTests(TestCase, TagTestingMixin):
    """
    Tests for the form generation code in L{LiveForm}.
    """
    # Minimal tag which can be used with the form renderer.  Classes are only
    # used to tell nodes apart in the tests.
    simpleLiveFormTag = div[
        span(pattern='text-input-container'),
        span(pattern='password-input-container'),
        span(pattern='form-input-container'),
        span(pattern='liveform', _class='liveform-container'),
        span(pattern='subform', _class='subform-container')]


    def test_compact(self):
        """
        L{LiveForm.compact} should replace the existing C{docFactory} with one
        for the I{compact} version of the live form template.
        """
        form = LiveForm(None, [])
        form.compact()
        self.assertTrue(form.docFactory.template.endswith('/liveform-compact.html'))


    def test_recursiveCompact(self):
        """
        L{LiveForm.compact} should also call C{compact} on all of its subforms.
        """
        class StubChild(object):
            compacted = False
            def compact(self):
                self.compacted = True
        child = StubChild()
        form = LiveForm(None, [Parameter('foo', FORM_INPUT, child),
                               Parameter('bar', TEXT_INPUT, int),
                               ListParameter('baz', None, 3),
                               ChoiceParameter('quux', [])])
        form.compact()
        self.assertTrue(child.compacted)


    def test_descriptionSlot(self):
        """
        L{LiveForm.form} should fill the I{description} slot on the tag it is
        passed with the description of the form.
        """
        description = u"the form description"
        formFragment = LiveForm(None, [], description)
        formTag = formFragment.form(None, self.simpleLiveFormTag)
        self.assertEqual(formTag.slotData['description'], description)


    def test_formSlotOuter(self):
        """
        When it is not nested inside another form, L{LiveForm.form} should fill
        the I{form} slot on the tag with the tag's I{liveform} pattern.
        """
        def submit(**kw):
            pass
        formFragment = LiveForm(submit, [])
        formTag = formFragment.form(None, self.simpleLiveFormTag)
        self.assertTag(
            formTag.slotData['form'], 'span', {'class': 'liveform-container'},
            [])


    def test_formSlotInner(self):
        """
        When it has a sub-form name, L{LiveForm.form} should fill the I{form}
        slot on the tag with the tag's I{subform} pattern.
        """
        def submit(**kw):
            pass
        formFragment = LiveForm(submit, [])
        formFragment.subFormName = 'test-subform'
        formTag = formFragment.form(None, self.simpleLiveFormTag)
        self.assertTag(
            formTag.slotData['form'], 'span', {'class': 'subform-container'},
            [])


    def test_noParameters(self):
        """
        When there are no parameters, L{LiveForm.form} should fill the
        I{inputs} slot on the tag it uses to fill the I{form} slot with an
        empty list.
        """
        def submit(**kw):
            pass
        formFragment = LiveForm(submit, [])
        formTag = formFragment.form(None, self.simpleLiveFormTag)
        self.assertEqual(formTag.slotData['form'].slotData['inputs'], [])


    def test_parameterViewOverride(self):
        """
        L{LiveForm.form} should use the C{view} attribute of parameter objects,
        if it is not C{None}, to fill the I{inputs} slot on the tag it uses to
        fill the I{form} slot.
        """
        def submit(**kw):
            pass

        name = u'param name'
        label = u'param label'
        type = TEXT_INPUT
        coercer = lambda value: value
        description = u'param desc'
        default = u'param default value'

        view = StubView()
        views = {}
        viewFactory = views.get
        param = Parameter(
            name, type, coercer, label, description, default, viewFactory)
        views[param] = view

        formFragment = LiveForm(submit, [param])
        formTag = formFragment.form(None, self.simpleLiveFormTag)
        self.assertEqual(
            formTag.slotData['form'].slotData['inputs'],
            [view])


    def test_individualTextParameter(self):
        """
        L{LiveForm.form} should fill the I{inputs} slot on the tag it uses to
        fill the I{form} slot with a list consisting of one
        L{TextParameterView} when the L{LiveForm} is created with one
        C{TEXT_INPUT} L{Parameter}.
        """
        def submit(**kw):
            pass

        name = u'param name'
        label = u'param label'
        type = TEXT_INPUT
        coercer = lambda value: value
        description = u'param desc'
        default = u'param default value'
        param = Parameter(
            name, type, coercer, label, description, default)

        formFragment = LiveForm(submit, [param])
        formTag = formFragment.form(None, self.simpleLiveFormTag)
        self.assertEqual(
            formTag.slotData['form'].slotData['inputs'],
            [TextParameterView(param)])


    def test_individualPasswordParameter(self):
        """
        L{LiveForm.form} should fill the I{inputs} slot of the tag it uses to
        fill the I{form} slot with a list consisting of one
        L{TextParameterView} when the L{LiveForm} is created with one
        C{PASSWORD_INPUT} L{Parameter}.
        """
        def submit(**kw):
            pass

        name = u'param name'
        label = u'param label'
        type = PASSWORD_INPUT
        coercer = lambda value: value
        description = u'param desc'
        default = u'param default value'
        param = Parameter(
            name, type, coercer, label, description, default)

        formFragment = LiveForm(submit, [param])
        formTag = formFragment.form(None, self.simpleLiveFormTag)
        self.assertEqual(
            formTag.slotData['form'].slotData['inputs'],
            [PasswordParameterView(param)])


    def test_individualFormParameter(self):
        """
        L{LiveForm.form} should fill the I{inputs} slot of the tag it uses to
        fill the I{form} slot with a list consisting of one
        L{FormParameterView} when the L{LiveForm} is created with one
        L{FormParameter}.
        """
        parameter = FormParameter(u'form param', LiveForm(None, []))
        formFragment = LiveForm(lambda **kw: None, [parameter])
        formTag = formFragment.form(None, self.simpleLiveFormTag)
        self.assertEqual(
            formTag.slotData['form'].slotData['inputs'],
            [FormParameterView(parameter)])


    def test_individualFormInputParameter(self):
        """
        L{LiveForm.form} should fill the I{inputs} slot of the tag it uses to
        fill the I{form} slot with a list consisting of one
        L{FormInputParameterView} when the L{LiveForm} is created with one
        C{FORM_INPUT} L{Parameter}.
        """
        def submit(**kw):
            pass

        name = u'param name'
        type = FORM_INPUT
        coercer = LiveForm(None, [])
        param = Parameter(name, type, coercer)

        formFragment = LiveForm(submit, [param])
        formTag = formFragment.form(None, self.simpleLiveFormTag)
        self.assertEqual(
            formTag.slotData['form'].slotData['inputs'],
            [FormInputParameterView(param)])


    def test_liveformTemplateStructuredCorrectly(self):
        """
        When a L{LiveForm} is rendered using the default template, the form
        contents should end up inside the I{form} tag.

        As I understand it, this is a necessary condition for the resulting
        html form to operate properly.  However, due to the complex behavior of
        the HTML (or even XHTML) DOM and the inscrutability of the various
        specific implementations of it, it is not entirely unlikely that my
        understanding is, in some way, flawed.  If you know better, and believe
        this test to be in error, supplying a superior test or simply deleting
        this one may not be out of the question. -exarkun
        """
        def submit(**kw):
            pass

        name = u'param name'
        label = u'param label'
        type = PASSWORD_INPUT
        coercer = lambda value: value
        description = u'param desc'
        default = u'param default value'
        param = Parameter(
            name, type, coercer, label, description, default)

        formFragment = LiveForm(submit, [param])
        html = renderLiveFragment(formFragment)
        document = parseString(html)
        forms = document.getElementsByTagName('form')
        self.assertEqual(len(forms), 1)
        inputs = forms[0].getElementsByTagName('input')
        self.assertTrue(len(inputs) >= 1)


    def test_liveFormJSClass(self):
        """
        Verify that the C{jsClass} attribute of L{LiveForm} is
        L{_LIVEFORM_JS_CLASS}.
        """
        self.assertEqual(LiveForm.jsClass, _LIVEFORM_JS_CLASS)


    def test_subFormJSClass(self):
        """
        Verify that the C{jsClass} attribute of the form returned from
        L{LiveForm.asSubForm} is L{_SUBFORM_JS_CLASS}.
        """
        liveForm = LiveForm(lambda **k: None, ())
        subForm = liveForm.asSubForm(u'subform')
        self.assertEqual(subForm.jsClass, _SUBFORM_JS_CLASS)


    def test_invoke(self):
        """
        L{LiveForm.invoke} should take the post dictionary it is passed, call
        the coercer for each of its parameters, take the output from each,
        whether it is available synchronously or as a Deferred result, and pass
        the aggregate to the callable the L{LiveForm} was instantiated with.  It
        should return a L{Deferred} which fires with the result of the callable
        when it is available.
        """
        arguments = {}
        submitResult = object()
        def submit(**args):
            arguments.update(args)
            return submitResult

        syncCoerces = []
        syncResult = object()
        def syncCoercer(value):
            syncCoerces.append(value)
            return syncResult
        sync = Parameter(u'sync', None, syncCoercer, None, None, None)

        asyncCoerces = []
        asyncResult = Deferred()
        def asyncCoercer(value):
            asyncCoerces.append(value)
            return asyncResult
        async = Parameter(u'async', None, asyncCoercer, None, None, None)

        form = LiveForm(submit, [sync, async])
        invokeResult = form.invoke({sync.name: [u'sync value'],
                                    async.name: [u'async value']})

        # Both of the coercers should have been called with their respective
        # values.
        self.assertEqual(syncCoerces, [u'sync value'])
        self.assertEqual(asyncCoerces, [u'async value'])

        # The overall form callable should not have been called yet, since a
        # Deferred is still outstanding.
        self.assertEqual(arguments, {})

        # This will be the result of the Deferred from asyncCoercer
        asyncObject = object()

        def cbInvoke(result):
            self.assertEqual(result, submitResult)
            self.assertEqual(arguments, {sync.name: syncResult,
                                         async.name: asyncObject})
        invokeResult.addCallback(cbInvoke)
        asyncResult.callback(asyncObject)
        return invokeResult


    def test_callingInvokes(self):
        """
        Calling a LiveForm should be the same as calling its invoke method. 
        This isn't a public API.
        """
        returnValue = object()
        calledWith = []
        def coercer(**params):
            calledWith.append(params)
            return returnValue

        form = LiveForm(
            coercer, [Parameter(u'name', TEXT_INPUT, unicode,
                                u'label', u'descr', u'default')])
        result = form({u'name': [u'value']})
        self.assertEqual(calledWith, [{u'name': u'value'}])
        result.addCallback(self.assertIdentical, returnValue)
        return result



class ListChangeParameterViewTestCase(TestCase):
    """
    Tests for L{ListChangeParameterView}.
    """
    def setUp(self):
        class TestableLiveForm(LiveForm):
            _isCompact = False
            def compact(self):
                self._isCompact = True
        self.innerParameters = [Parameter('foo', TEXT_INPUT, int)]
        self.parameter = ListChangeParameter(
            u'repeatableFoo', self.innerParameters, defaults=[], modelObjects=[])
        self.parameter.liveFormFactory = TestableLiveForm
        self.parameter.repeatedLiveFormWrapper = RepeatedLiveFormWrapper
        self.view = ListChangeParameterView(self.parameter)


    def test_patternName(self):
        """
        L{ListChangeParameterView} should use I{repeatable-form} as its
        C{patternName}
        """
        self.assertEqual(self.view.patternName, 'repeatable-form')


    def _doSubFormTest(self, subFormWrapper):
        """
        C{subFormWrapper} (which we expect to be the result of
        L{self.parameter.formFactory}, wrapped in
        L{self.parameter.repeatedLiveFormWrapper) should be a render-ready
        liveform that knows its a subform.
        """
        self.failUnless(
            isinstance(subFormWrapper, RepeatedLiveFormWrapper))
        self.assertIdentical(subFormWrapper.fragmentParent, self.view)
        subForm = subFormWrapper.liveForm
        self.assertEqual(self.innerParameters, subForm.parameters)
        self.assertEqual(subForm.subFormName, self.parameter.name)


    def test_formsRendererReturnsSubForm(self):
        """
        The C{forms} renderer of L{ListChangeParameterView} should render
        the liveform that was passed to the underlying parameter, as a
        subform.
        """
        (form,) = renderer.get(self.view, 'forms')(None, None)
        self._doSubFormTest(form)


    def test_repeatFormReturnsSubForm(self):
        """
        The C{repeatForm} exposed method of L{ListChangeParameterView}
        should return the liveform that was passed to the underlying
        parameter, as a subform.
        """
        self._doSubFormTest(expose.get(self.view, 'repeatForm')())


    def test_formsRendererCompact(self):
        """
        The C{forms} renderer of L{ListChangeParameterView} should call
        C{compact} on the form it returns, if the parameter it is wrapping had
        C{compact} called on it.
        """
        self.parameter.compact()
        (renderedForm,) = renderer.get(self.view, 'forms')(None, None)
        self.failUnless(renderedForm.liveForm._isCompact)


    def test_repeatFormCompact(self):
        """
        The C{repeatForm} exposed method of of L{ListChangeParameterView}
        should call C{compact} on the form it returns, if the parameter it is
        wrapping had C{compact} called on it.
        """
        self.parameter.compact()
        renderedForm = expose.get(self.view, 'repeatForm')()
        self.failUnless(renderedForm.liveForm._isCompact)


    def test_formsRendererNotCompact(self):
        """
        The C{forms} renderer of L{ListChangeParameterView} shouldn't call
        C{compact} on the form it returns, unless the parameter it is wrapping
        had C{compact} called on it.
        """
        (renderedForm,) = renderer.get(self.view, 'forms')(None, None)
        self.failIf(renderedForm.liveForm._isCompact)


    def test_repeatFormNotCompact(self):
        """
        The C{repeatForm} exposed method of L{ListChangeParameterView}
        shouldn't call C{compact} on the form it returns, unless the parameter
        it is wrapping had C{compact} called on it.
        """
        renderedForm = expose.get(self.view, 'repeatForm')()
        self.failIf(renderedForm.liveForm._isCompact)


    def test_repeaterRenderer(self):
        """
        The C{repeater} renderer of L{ListChangeParameterView} should
        return an instance of the C{repeater} pattern from its docFactory.
        """
        self.view.docFactory = stan(div(pattern='repeater', foo='bar'))
        renderedTag = renderer.get(self.view, 'repeater')(None, None)
        self.assertEqual(renderedTag.attributes['foo'], 'bar')



class ListChangeParameterTestCase(TestCase):
    """
    Tests for L{ListChangeParameter}.
    """
    _someParameters = (Parameter('foo', TEXT_INPUT, int),)

    def setUp(self):
        self.innerParameters = [Parameter('foo', TEXT_INPUT, int)]
        self.defaultValues = {u'foo': -56}
        self.defaultObject = object()

        self.parameter = ListChangeParameter(
            u'repeatableFoo', self.innerParameters,
            defaults=[self.defaultValues],
            modelObjects=[self.defaultObject])


    def getListChangeParameter(self, parameters, defaults):
        return ListChangeParameter(
            name=u'stateRepeatableFoo', parameters=parameters,
            defaults=defaults,
            modelObjects=[object() for i in range(len(defaults))])


    def test_asLiveForm(self):
        """
        L{ListChangeParameter.asLiveForm} should wrap forms in
        L{ListChangeParameter.liveFormWrapperFactory}.
        """
        parameter = self.getListChangeParameter(self._someParameters, [])
        parameter.repeatedLiveFormWrapper = RepeatedLiveFormWrapper

        liveFormWrapper = parameter.asLiveForm()
        self.failUnless(
            isinstance(liveFormWrapper, RepeatedLiveFormWrapper))
        self.assertTrue(liveFormWrapper.removable)
        liveForm = liveFormWrapper.liveForm
        self.failUnless(isinstance(liveForm, LiveForm))
        self.assertEqual(liveForm.subFormName, parameter.name)
        self.assertEqual(liveForm.parameters, self._someParameters)


    def test_getInitialLiveForms(self):
        """
        Same as L{test_asLiveForm}, but looks at the single liveform returned
        from L{ListChangeParameter.getInitialLiveForms} when the parameter
        was constructed with no defaults.
        """
        parameter = self.getListChangeParameter(self._someParameters, [])
        parameter.repeatedLiveFormWrapper = RepeatedLiveFormWrapper

        liveFormWrappers = parameter.getInitialLiveForms()
        self.assertEqual(len(liveFormWrappers), 1)

        liveFormWrapper = liveFormWrappers[0]
        self.failUnless(
            isinstance(liveFormWrapper, RepeatedLiveFormWrapper))
        self.assertFalse(liveFormWrapper.removable)
        liveForm = liveFormWrapper.liveForm
        self.failUnless(isinstance(liveForm, LiveForm))
        self.assertEqual(liveForm.subFormName, parameter.name)
        self.assertEqual(liveForm.parameters, self._someParameters)


    def test_getInitialLiveFormsDefaults(self):
        """
        Same as L{test_getInitialLiveForms}, but for the case where the
        parameter was constructed with default values.
        """
        defaults = [{'foo': 1}, {'foo': 3}]
        parameter = self.getListChangeParameter(self._someParameters, defaults)
        parameter.repeatedLiveFormWrapper = RepeatedLiveFormWrapper

        liveFormWrappers = parameter.getInitialLiveForms()
        self.assertEqual(len(liveFormWrappers), len(defaults))
        for (liveFormWrapper, default) in zip(liveFormWrappers, defaults):
            self.failUnless(
                isinstance(liveFormWrapper, RepeatedLiveFormWrapper))
            self.assertTrue(liveFormWrapper.removable)

            liveForm = liveFormWrapper.liveForm
            self.failUnless(isinstance(liveForm, LiveForm))
            self.assertEqual(liveForm.subFormName, parameter.name)
            self.assertEqual(len(liveForm.parameters), 1)

            # Matches up with self._someParameters, except the default should
            # be different.
            innerParameter = liveForm.parameters[0]
            self.assertEqual(innerParameter.name, 'foo')
            self.assertEqual(innerParameter.type, TEXT_INPUT)
            self.assertEqual(innerParameter.coercer, int)
            self.assertEqual(innerParameter.default, default['foo'])


    def test_identifierMapping(self):
        """
        L{ListChangeParameter} should be able to freely convert between
        python objects and the opaque identifiers generated from them.
        """
        defaultObject = object()
        identifier = self.parameter._idForObject(defaultObject)
        self.assertIdentical(
            self.parameter._objectFromID(identifier), defaultObject)


    def test_extractCreations(self):
        """
        L{RepeatableFormParameter._extractCreations} should return a list of
        two-tuples giving the identifiers of new objects being created and
        their associated uncoerced arguments.
        """
        key = u'key'

        (modificationIdentifier,) = self.parameter._idsToObjects.keys()
        modificationValue = u'edited value'

        creationIdentifier = self.parameter._newIdentifier()
        creationValue = u'created value'

        dataSets = [
            {self.parameter._IDENTIFIER_KEY: creationIdentifier,
             key: creationValue},
            {self.parameter._IDENTIFIER_KEY: modificationIdentifier,
             key: modificationValue}]

        creations = list(self.parameter._extractCreations(dataSets))
        self.assertEqual(creations, [(creationIdentifier, {key: creationValue})])


    def test_extractEdits(self):
        """
        L{RepeatableFormParameter._extractEdits} should return a list of
        two-tuples giving the identifiers of existing model objects which might
        be about to change and their associated uncoerced arguments.
        """
        key = u'key'

        creationIdentifier = self.parameter._newIdentifier()
        creationValue = u'created value'

        modificationIdentifier = self.parameter._idForObject(
            self.defaultObject)
        modificationValue = u'edited value'

        dataSets = [
            {self.parameter._IDENTIFIER_KEY: creationIdentifier,
             key: creationValue},
            {self.parameter._IDENTIFIER_KEY: modificationIdentifier,
             key: modificationValue}]

        edits = list(self.parameter._extractEdits(dataSets))
        self.assertEqual(
            edits, [(modificationIdentifier, {key: modificationValue})])


    def test_coerceAll(self):
        """
        L{RepeatableFormParameter._coerceAll} should take a list of two-tuples
        and return a L{Deferred} which is called back with a list of tuples
        where the first element of each tuple is the first element of a tuple
        from the input and the second element of each tuple is the result of
        the L{Deferred} returned by a call to
        L{RepeatableFormParameter._coerceSingleRepetition} with the second
        element of the same tuple from the input.  The ordering of the input
        and output lists should be the same.
        """
        firstInput = object()
        firstValue = u'1'
        secondInput = object()
        secondValue = u'2'
        inputs = [(firstInput, {u'foo': firstValue}),
                  (secondInput, {u'foo': secondValue})]

        coerceDeferred = self.parameter._coerceAll(inputs)
        coerceDeferred.addCallback(
            self.assertEqual,
            [(firstInput, {u'foo': int(firstValue)}),
             (secondInput, {u'foo': int(secondValue)})])
        return coerceDeferred


    def test_coercion(self):
        """
        L{ListChangeParameter._coerceSingleRepetition} should call the
        appropriate coercers from the repeatable form's parameters.
        """
        d = self.parameter._coerceSingleRepetition({u'foo': [u'-56']})
        d.addCallback(self.assertEqual, {u'foo': -56})
        return d


    def test_coercerCreate(self):
        """
        L{ListChangeParameter.coercer} should be able to figure out that a
        repetition is new if it is associated with an identifier generated by
        C{asLiveForm}.
        """
        parameter = ListChangeParameter(
            u'repeatableFoo', self.innerParameters,
            defaults=[],
            modelObjects=[])

        # get an id allocated to us
        liveFormWrapper = parameter.asLiveForm()
        coerceDeferred = parameter.coercer(
            [{u'foo': [u'-56'],
              parameter._IDENTIFIER_KEY: liveFormWrapper.identifier}])
        def cbCoerced(submission):
            self.assertEqual(submission.edit, [])
            self.assertEqual(submission.delete, [])
            self.assertEqual(len(submission.create), 1)
            self.assertEqual(submission.create[0].values, {u'foo': -56})
            CREATED_OBJECT = object()
            submission.create[0].setter(CREATED_OBJECT)
            self.assertIdentical(
                parameter._objectFromID(liveFormWrapper.identifier),
                CREATED_OBJECT)
        coerceDeferred.addCallback(cbCoerced)
        return coerceDeferred


    def test_coercerCreateNoChange(self):
        """
        L{ListChangeParameter.coercer} should be able to figure out when
        nothing has been done to a set of values created by a previous
        submission.
        """
        parameter = ListChangeParameter(
            u'repeatableFoo', self.innerParameters,
            defaults=[],
            modelObjects=[])

        # get an id allocated to us
        liveFormWrapper = parameter.asLiveForm()
        identifier = liveFormWrapper.identifier

        value = {u'foo': [u'-56'], parameter._IDENTIFIER_KEY: identifier}
        coerceDeferred = parameter.coercer([value.copy()])

        def cbFirstSubmit(firstSubmission):
            firstSubmission.create[0].setter(None)

            # Resubmit the same thing
            return parameter.coercer([value.copy()])

        def cbSecondSubmit(secondSubmission):
            self.assertEqual(secondSubmission.create, [])
            self.assertEqual(secondSubmission.edit, [])
            self.assertEqual(secondSubmission.delete, [])

        coerceDeferred.addCallback(cbFirstSubmit)
        coerceDeferred.addCallback(cbSecondSubmit)
        return coerceDeferred


    def test_coercerEdit(self):
        """
        L{ListChangeParameter.coercer} should be able to figure out that a
        repetition is an edit if its identifier corresponds to an entry in the
        list of defaults.
        """
        (identifier,) = self.parameter._idsToObjects.keys()

        editDeferred = self.parameter.coercer(
            [{u'foo': [u'-57'],
              self.parameter._IDENTIFIER_KEY: identifier}])

        def cbEdit(submission):
            self.assertEqual(submission.create, [])
            self.assertEqual(submission.edit,
                             [EditObject(self.defaultObject, {u'foo': -57})])
            self.assertEqual(submission.delete, [])

        editDeferred.addCallback(cbEdit)
        return editDeferred


    def test_repeatedCoercerEdit(self):
        """
        L{ListChangeParameter.coercer} should work correctly with respect
        to repeated edits.
        """
        (identifier,) = self.parameter._idsToObjects.keys()

        editDeferred = self.parameter.coercer(
            [{u'foo': [u'-57'], self.parameter._IDENTIFIER_KEY: identifier}])

        def cbEdited(ignored):
            # edit it back to the initial value
            return self.parameter.coercer(
                [{u'foo': [u'-56'], self.parameter._IDENTIFIER_KEY: identifier}])

        def cbRestored(submission):
            self.assertEqual(submission.create, [])
            self.assertEqual(submission.edit,
                             [EditObject(self.defaultObject, {u'foo': -56})])
            self.assertEqual(submission.delete, [])

        editDeferred.addCallback(cbEdited)
        editDeferred.addCallback(cbRestored)
        return editDeferred


    def test_coercerNoChange(self):
        """
        L{ListChangeParameter.coercer} shouldn't include a repetition
        anywhere in its result if it corresponds to a default and wasn't
        edited.
        """
        (identifier,) = self.parameter._idsToObjects.keys()

        unchangedDeferred = self.parameter.coercer(
            [{u'foo': [u'-56'],
              self.parameter._IDENTIFIER_KEY: identifier}])

        def cbUnchanged(submission):
            self.assertEqual(submission.create, [])
            self.assertEqual(submission.edit, [])
            self.assertEqual(submission.delete, [])

        unchangedDeferred.addCallback(cbUnchanged)
        return unchangedDeferred


    def test_repeatedCoercerNoChange(self):
        """
        Same as L{test_coercerNoChange}, but with multiple submissions that
        don't change anything.
        """
        (identifier,) = self.parameter._idsToObjects.keys()

        editDeferred = self.parameter.coercer(
            [{u'foo': [u'-56'],
              self.parameter._IDENTIFIER_KEY: identifier}])

        def cbEdited(ignored):
            # Same values - no edit occurs.
            return self.parameter.coercer(
                [{u'foo': [u'-56'],
                  self.parameter._IDENTIFIER_KEY: identifier}])

        def cbUnedited(submission):
            self.assertEqual(submission.create, [])
            self.assertEqual(submission.edit, [])
            self.assertEqual(submission.delete, [])

        editDeferred.addCallback(cbEdited)
        editDeferred.addCallback(cbUnedited)
        return editDeferred


    def test_coercerDelete(self):
        """
        L{ListChangeParameter.coercer} should be able to figure out that a
        default was deleted if it doesn't get a repetition with a
        corresponding identifier.
        """
        deleteDeferred = self.parameter.coercer([])

        def cbDeleted(submission):
            self.assertEqual(submission.create, [])
            self.assertEqual(submission.edit, [])
            self.assertEqual(submission.delete, [self.defaultObject])

        deleteDeferred.addCallback(cbDeleted)
        return deleteDeferred


    def test_repeatedCoercerDelete(self):
        """
        L{ListChangeParameter.coercer} should only report a deletion the
        first time that it doesn't see a particular value.
        """
        deleteDeferred = self.parameter.coercer([])

        def cbDeleted(ignored):
            return self.parameter.coercer([])

        def cbUnchanged(submission):
            self.assertEqual(submission.create, [])
            self.assertEqual(submission.edit, [])
            self.assertEqual(submission.delete, [])

        deleteDeferred.addCallback(cbDeleted)
        deleteDeferred.addCallback(cbUnchanged)
        return deleteDeferred


    def test_coercerDeleteUnsubmitted(self):
        """
        L{ListChangeParameter.coercer} should not report as deleted an
        internal marker objects when a form is repeated but the repetition is
        omitted from the submission.
        """
        (identifier,) = self.parameter._idsToObjects.keys()

        # Creates some new state inside the parameter (yea, ick, state).
        repetition = self.parameter.asLiveForm()
        unchangedDeferred = self.parameter.coercer([
            {u'foo': [u'-56'],
             self.parameter._IDENTIFIER_KEY: identifier}])

        def cbUnchanged(submission):
            self.assertEqual(submission.create, [])
            self.assertEqual(submission.edit, [])
            self.assertEqual(submission.delete, [])

        unchangedDeferred.addCallback(cbUnchanged)
        return unchangedDeferred


    def test_makeDefaultLiveForm(self):
        """
        L{ListChangeParameter._makeDefaultLiveForm} should make a live
        form that has been correctly wrapped and initialized.
        """
        liveFormWrapper = self.parameter._makeDefaultLiveForm(
            (self.parameter.defaults[0], 1234))
        self.failUnless(isinstance(
            liveFormWrapper, self.parameter.repeatedLiveFormWrapper))
        liveForm = liveFormWrapper.liveForm
        self.failUnless(isinstance(liveForm, LiveForm))
        self.assertEqual(
            len(liveForm.parameters), len(self.innerParameters))
        for parameter in liveForm.parameters:
            self.assertEqual(parameter.default, self.defaultValues[parameter.name])


    def test_makeADefaultLiveFormChoiceParameter(self):
        """
        Verify that the parameter-defaulting done by
        L{ListChangeParameter._makeDefaultLiveForm} works for
        L{ChoiceParameter} instances.
        """
        param = ListChangeParameter(
            u'',
            [ChoiceParameter(
                u'choice',
                [Option(u'opt 1', u'1', True),
                 Option(u'opt 2', u'2', False)],
                u'label!',
                u'description!',
                multiple=True)])
        liveFormWrapper = param._makeDefaultLiveForm(
            ({u'choice': [u'1', u'2']}, 1234))
        liveForm = liveFormWrapper.liveForm
        clonedParams = liveForm.parameters
        self.assertEqual(len(clonedParams), 1)
        clonedChoiceParam = clonedParams[0]
        self.assertTrue(
            isinstance(clonedChoiceParam, ChoiceParameter))
        self.assertEqual(clonedChoiceParam.name, u'choice')
        self.assertEqual(clonedChoiceParam.label, u'label!')
        self.assertEqual(
            clonedChoiceParam.description, u'description!')
        self.assertTrue(clonedChoiceParam.multiple)

        self.assertEqual(len(clonedChoiceParam.choices), 2)
        (c1, c2) = clonedChoiceParam.choices
        self.assertEqual(c1.description, u'opt 1')
        self.assertEqual(c1.value, u'1')
        self.assertEqual(c1.selected, True)
        self.assertEqual(c2.description, u'opt 2')
        self.assertEqual(c2.value, u'2')
        self.assertEqual(c2.selected, True)


    def test_asLiveFormIdentifier(self):
        """
        L{ListChangeParameter.asLiveForm} should allocate an identifier
        for the new liveform, pass it to the liveform wrapper and put the
        placeholder value L{ListChangeParameter._NO_OBJECT_MARKER} into
        the object mapping.
        """
        liveFormWrapper = self.parameter.asLiveForm()
        self.assertIn(liveFormWrapper.identifier, self.parameter._idsToObjects)
        self.assertIdentical(
            self.parameter._objectFromID(liveFormWrapper.identifier),
            self.parameter._NO_OBJECT_MARKER)


    def test_correctIdentifiersFromGetInitialLiveForms(self):
        """
        L{ListChangeParameter.getInitialLiveForms} should return a list of
        L{RepeatedLiveFormWrapper} instances with C{identifier} attributes
        which correspond to the identifiers associated with corresponding
        model objects in the L{ListChangeParameter}.
        """
        # XXX This should really have more than one model object to make sure
        # ordering is tested properly.
        forms = self.parameter.getInitialLiveForms()
        self.assertEqual(len(forms), 1)
        self.assertIdentical(
            self.parameter._objectFromID(forms[0].identifier),
            self.defaultObject)


    def test_fromInputs(self):
        """
        L{RepeatableFormParameter.fromInputs} should call the appropriate
        coercers from the repeatable form's parameters.
        """
        (modifyIdentifier,) = self.parameter._idsToObjects.keys()

        # Make a new object to be deleted
        deleteObject = object()
        deleteIdentifier = self.parameter._idForObject(deleteObject)

        createIdentifier = self.parameter._newIdentifier()

        result = self.parameter.fromInputs({
                self.parameter.name: [[
                        {self.parameter._IDENTIFIER_KEY: modifyIdentifier,
                         u'foo': [u'-57']},
                        {self.parameter._IDENTIFIER_KEY: createIdentifier,
                         u'foo': [u'18']}]]})
        def cbCoerced(changes):
            self.assertEqual(len(changes.create), 1)
            self.assertEqual(changes.create[0].values, {u'foo': 18})
            self.assertEqual(len(changes.edit), 1)

            self.assertIdentical(changes.edit[0].object, self.defaultObject)
            self.assertEqual(changes.edit[0].values, {u'foo': -57})

            self.assertEqual(changes.delete, [deleteObject])

        result.addCallback(cbCoerced)
        return result



class RepeatedLiveFormWrapperTestCase(TestCase):
    """
    Tests for L{RepeatedLiveFormWrapper}.
    """
    def test_removeLinkRenderer(self):
        """
        Verify that the I{removeLink} renderer of L{RepeatedLiveFormWrapper}
        only returns the tag if the C{removable} argument passed to the
        constructor is C{True}.
        """
        fragment = RepeatedLiveFormWrapper(None, None, removable=True)
        removeLinkRenderer = renderer.get(fragment, 'removeLink', None)
        tag = div()
        self.assertIdentical(removeLinkRenderer(None, tag), tag)
        fragment.removable = False
        self.assertEqual(removeLinkRenderer(None, tag), '')
