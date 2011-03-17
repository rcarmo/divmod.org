# -*- test-case-name: xmantissa.test.test_liveform -*-

"""

XXX HYPER TURBO SUPER UNSTABLE DO NOT USE XXX

"""

import warnings

from zope.interface import implements

from twisted.python.components import registerAdapter
from twisted.internet.defer import maybeDeferred, gatherResults

from epsilon.structlike import record

from nevow import inevow, tags, page, athena
from nevow.athena import expose
from nevow.page import Element, renderer
from nevow.loaders import stan

from xmantissa import webtheme
from xmantissa.fragmentutils import PatternDictionary, dictFillSlots
from xmantissa.ixmantissa import IParameter, IParameterView


_LIVEFORM_JS_CLASS = u'Mantissa.LiveForm.FormWidget'
_SUBFORM_JS_CLASS = u'Mantissa.LiveForm.SubFormWidget'



class InputError(athena.LivePageError):
    """
    Base class for all errors related to rejected input values.
    """
    jsClass = u'Mantissa.LiveForm.InputError'



TEXT_INPUT = 'text'
PASSWORD_INPUT = 'password'
TEXTAREA_INPUT = 'textarea'
FORM_INPUT = 'form'
RADIO_INPUT = 'radio'
CHECKBOX_INPUT = 'checkbox'



class _SelectiveCoercer(object):
    """
    Mixin defining a L{IParameter.fromInputs} implementation which extracts the
    input associated with this parameter based on C{self.name} and passes it to
    C{self.coercer}, returning the result.
    """
    def fromInputs(self, inputs):
        """
        Extract the inputs associated with the child forms of this parameter
        from the given dictionary and coerce them using C{self.coercer}.

        @type inputs: C{dict} mapping C{unicode} to C{list} of C{unicode}
        @param inputs: The contents of a form post, in the conventional
            structure.

        @rtype: L{Deferred}
        @return: The structured data associated with this parameter represented
            by the post data.
        """
        try:
            values = inputs[self.name]
        except KeyError:
            raise ConfigurationError(
                "Missing value for input: " + self.name)
        return self.coerceMany(values)


    def coerceMany(self, values):
        """
        Convert the given C{list} of C{unicode} inputs to structured data.

        @param values: The inputs associated with this parameter's name in the
            overall inputs mapping.
        """
        return self.coercer(values[0])



class Parameter(record('name type coercer label description default '
                       'viewFactory',
                       label=None,
                       description=None,
                       default=None,
                       viewFactory=IParameterView), _SelectiveCoercer):
    """
    @type name: C{unicode}
    @ivar name: A name uniquely identifying this parameter within a particular
        form.

    @ivar type: One of C{TEXT_INPUT}, C{PASSWORD_INPUT}, C{TEXTAREA_INPUT},
        C{RADIO_INPUT}, or C{CHECKBOX_INPUT} indicating the kind of input
        interface which will be presented for this parameter.

    @type description: C{unicode} or C{NoneType}
    @ivar description: An explanation of the meaning or purpose of this
        parameter which will be presented in the view, or C{None} if the user
        is intended to guess.

    @type default: C{unicode} or C{NoneType}
    @ivar default: A value which will be initially presented in the view as the
        value for this parameter, or C{None} if no such value is to be
        presented.

    @ivar viewFactory: A two-argument callable which returns an
        L{IParameterView} provider which will be used as the view for this
        parameter, if one can be provided.  It will be invoked with the
        parameter as the first argument and a default value as the second
        argument.  The default should be returned if no view can be provided
        for the given parameter.
    """
    implements(IParameter)

    def __init__(self, *a, **kw):
        super(Parameter, self).__init__(*a, **kw)
        if self.type == FORM_INPUT:
            warnings.warn(
                "Create a FormParameter, not a Parameter with type FORM_INPUT",
                category=DeprecationWarning,
                stacklevel=2)


    def compact(self):
        """
        Compact FORM_INPUTs by calling their C{compact} method.  Don't do
        anything for other types of input.
        """
        if self.type == FORM_INPUT:
            self.coercer.compact()


    def clone(self, default):
        """
        Make a copy of this parameter, supplying a different default.

        @type default: C{unicode} or C{NoneType}
        @param default: A value which will be initially presented in the view
        as the value for this parameter, or C{None} if no such value is to be
        presented.

        @rtype: L{Parameter}
        """
        return self.__class__(
            self.name,
            self.type,
            self.coercer,
            self.label,
            self.description,
            default,
            self.viewFactory)



class FormParameter(record('name form label description default viewFactory',
                           label=None, description=None, default=None,
                           viewFactory=IParameterView),
                    _SelectiveCoercer):
    """
    A parameter which is a collection of other parameters, as composed by a
    L{LiveForm}.

    @type name: C{unicode}
    @ivar name: A name uniquely identifying this parameter within a
    particular form.

    @type form: L{LiveForm}
    @ivar form: The form which defines the grouped parameters.

    @type description: C{unicode} or C{NoneType}
    @ivar description: An explanation of the meaning or purpose of this
        parameter which will be presented in the view, or C{None} if the user
        is intended to guess.

    @type default: C{unicode} or C{NoneType}
    @ivar default: A value which will be initially presented in the view as the
        value for this parameter, or C{None} if no such value is to be
        presented.

    @ivar viewFactory: A two-argument callable which returns an
        L{IParameterView} provider which will be used as the view for this
        parameter, if one can be provided.  It will be invoked with the
        parameter as the first argument and a default value as the second
        argument.  The default should be returned if no view can be provided
        for the given parameter.
    """
    implements(IParameter)

    type = FORM_INPUT

    def compact(self):
        """
        Compact the wrapped form.
        """
        self.form.compact()


    def coercer(self, value):
        """
        Invoke the wrapped form with the given value and return its result.
        """
        return self.form.invoke(value)



class CreateObject(record('values setter')):
    """
    Represent one object which should be created as a result of a submission to
    a L{ListChangeParameter}.

    @ivar values: The coerced data from the submission which should be used to
        create this object.

    @ivar setter: A one-argument callable which must be called with the created
        object once it is created.  Until this is called, the
        L{ListChangeParameter} will be in a state where it
        will not handle submissions correctly. (XXX - This could be hooked up
        to a Deferred, and L{ListChangeParameter}'s C{coercer}
        method could gatherResults() on all of these, delaying the success of
        the submission until all created objects have been set).
    """



class EditObject(record('object values')):
    """
    Represent changes to be made to an object as the result of the submission
    of a L{ListChangeParameter}.

    @ivar object: The object which is to be edited.  This is one of the
        elements of the C{modelObjects} sequence passed to
        L{ListChangeParameter.__init__} or it is one of the
        objects subsequently added to the L{ListChangeParameter} by
        a call to L{CreateObject.setter}.

    @ivar values: The new values for this object from the submission.
    """
    def __cmp__(self, other):
        return cmp((self.object, self.values), (other.object, other.values))



class ListChanges(record('create edit delete')):
    """
    Represent the submission of a L{ListChangeParameter}.

    @ivar create: A list of L{CreateObject} instances, one for each new object
        to be created as a result of the submission.

    @ivar edit: A list of L{EditObject} instances, one for each existing object
        modified by the submission.

    @ivar delete: A list of model objects which should be deleted as a result
        of the submission.
    """



class ListChangeParameter(record('name parameters defaults modelObjects '
                                 'modelObjectDescription viewFactory',
                                 defaults=(), modelObjects=(),
                                 modelObjectDescription=u'',
                                 viewFactory=IParameterView),
                          _SelectiveCoercer):
    """
    Use this parameter if you want to render lists of objects as forms, and to
    allow the objects to be edited and deleted, as well as to have new objects
    created.

    Parameters of this type will be coerced in L{ListChanges} objects.

    @type name: C{unicode}
    @ivar name: A name uniquely identifying this parameter within a
    particular form.

    @type parameters: C{list}
    @ivar parameters: sequence of L{Parameter} instances, describing the
    contents of the repeatable form.

    @type defaults: C{list}
    @ivar defaults: A sequence of dictionaries mapping names of L{parameters}
        to values.

    @type modelObjects: C{list}
    @ivar modelObjects: A sequence of opaque objects, one for each item in
    C{defaults}.

    @type modelObjectDescription: C{unicode}
    @param modelObjectDescription: A description of the type of model object
    being edited, e.g. 'Email Address'.  Defaults to the empty string.

    @type viewFactory: callable
    @ivar viewFactory: A two-argument callable which returns an
        L{IParameterView} provider which will be used as the view for this
        parameter, if one can be provided.  It will be invoked with the
        parameter as the first argument and a default value as the second
        argument.  The default should be returned if no view can be provided
        for the given parameter.
    """
    _parameterIsCompact = False
    type = None

    _IDENTIFIER_KEY = u'__repeated-liveform-id__'
    _NO_OBJECT_MARKER = object()

    def __init__(self, *a, **k):
        super(ListChangeParameter, self).__init__(*a, **k)
        self.liveFormFactory = LiveForm
        self.repeatedLiveFormWrapper = RepeatedLiveFormWrapper
        self._idsToObjects = {}
        self._lastValues = {}
        self._defaultStuff = []
        for (defaultObject, defaultValues) in zip(self.modelObjects, self.defaults):
            identifier = self._idForObject(defaultObject)
            self._lastValues[identifier] = defaultValues
            self._defaultStuff.append((defaultValues, identifier))


    def compact(self):
        """
        Remember whether we were compacted or not, so we can relay this to our
        view.
        """
        self._parameterIsCompact = True


    def _prepareSubForm(self, liveForm):
        """
        Utility for turning liveforms into subforms, and compacting them as
        necessary.

        @param liveForm: a liveform.
        @type liveForm: L{LiveForm}

        @return: a sub form.
        @rtype: L{LiveForm}
        """
        liveForm = liveForm.asSubForm(self.name) # XXX Why did this work???
        # if we are compact, tell the liveform so it can tell its parameters
        # also
        if self._parameterIsCompact:
            liveForm.compact()
        return liveForm


    def _cloneDefaultedParameter(self, original, default):
        """
        Make a copy of the parameter C{original}, supplying C{default} as the
        default value.

        @type original: L{Parameter} or L{ChoiceParameter}
        @param original: A liveform parameter.

        @param default: An alternate default value for the parameter.

        @rtype: L{Parameter} or L{ChoiceParameter}
        @return: A new parameter.
        """
        if isinstance(original, ChoiceParameter):
            default = [Option(o.description, o.value, o.value in default)
                        for o in original.choices]
        return original.clone(default)


    _counter = 0
    def _allocateID(self):
        """
        Allocate an internal identifier.

        @rtype: C{int}
        """
        self._counter += 1
        return self._counter


    def _idForObject(self, defaultObject):
        """
        Generate an opaque identifier which can be used to talk about
        C{defaultObject}.

        @rtype: C{int}
        """
        identifier = self._allocateID()
        self._idsToObjects[identifier] = defaultObject
        return identifier


    def _objectFromID(self, identifier):
        """
        Find the object associated with the identifier C{identifier}.

        @type identifier: C{int}
        """
        return self._idsToObjects[identifier]


    def _newIdentifier(self):
        """
        Make a new identifier for an as-yet uncreated model object.

        @rtype: C{int}
        """
        id = self._allocateID()
        self._idsToObjects[id] = self._NO_OBJECT_MARKER
        self._lastValues[id] = None
        return id


    def _makeALiveForm(self, parameters, identifier, removable=True):
        """
        Make a live form with the parameters C{parameters}, which will be used
        to edit the values/model object with identifier C{identifier}.

        @type parameters: C{list}
        @param parameters: list of L{Parameter} instances.

        @type identifier: C{int}

        @type removable: C{bool}

        @rtype: L{repeatedLiveFormWrapper}
        """
        liveForm = self.liveFormFactory(lambda **k: None, parameters, self.name)
        liveForm = self._prepareSubForm(liveForm)
        liveForm = self.repeatedLiveFormWrapper(liveForm, identifier, removable)
        liveForm.docFactory = webtheme.getLoader(liveForm.fragmentName)
        return liveForm


    def _makeDefaultLiveForm(self, (defaults, identifier)):
        """
        Make a liveform suitable for editing the set of default values C{defaults}.

        @type defaults: C{dict}
        @param defaults: Mapping of parameter names to values.

        @rtype: L{repeatedLiveFormWrapper}
        """
        parameters = [self._cloneDefaultedParameter(p, defaults[p.name])
                        for p in self.parameters]
        return self._makeALiveForm(parameters, identifier)


    def getInitialLiveForms(self):
        """
        Make and return as many L{LiveForm} instances as are necessary to hold
        our default values.

        @return: some subforms.
        @rtype: C{list} of L{LiveForm}
        """
        liveForms = []
        if self._defaultStuff:
            for values in self._defaultStuff:
                liveForms.append(self._makeDefaultLiveForm(values))
        else:
            # or only one, for the first new thing
            liveForms.append(
                self._makeALiveForm(
                    self.parameters, self._newIdentifier(), False))
        return liveForms


    def asLiveForm(self):
        """
        Make and return a form, using L{parameters}.

        @return: a sub form.
        @rtype: L{LiveForm}
        """
        return self._makeALiveForm(self.parameters, self._newIdentifier())


    def _coerceSingleRepetition(self, dataSet):
        """
        Make a new liveform with our parameters, and get it to coerce our data
        for us.
        """
        # make a liveform because there is some logic in _coerced
        form = LiveForm(lambda **k: None, self.parameters, self.name)
        return form.fromInputs(dataSet)


    def _extractCreations(self, dataSets):
        """
        Find the elements of C{dataSets} which represent the creation of new
        objects.

        @param dataSets: C{list} of C{dict} mapping C{unicode} form submission
            keys to form submission values.

        @return: iterator of C{tuple}s with the first element giving the opaque
            identifier of an object which is to be created and the second
            element giving a C{dict} of all the other creation arguments.
        """
        for dataSet in dataSets:
            modelObject = self._objectFromID(dataSet[self._IDENTIFIER_KEY])
            if modelObject is self._NO_OBJECT_MARKER:
                dataCopy = dataSet.copy()
                identifier = dataCopy.pop(self._IDENTIFIER_KEY)
                yield identifier, dataCopy


    def _extractEdits(self, dataSets):
        """
        Find the elements of C{dataSets} which represent changes to existing
        objects.

        @param dataSets: C{list} of C{dict} mapping C{unicode} form submission
            keys to form submission values.

        @return: iterator of C{tuple}s with the first element giving a model
            object which is being edited and the second element giving a
            C{dict} of all the other arguments.
        """
        for dataSet in dataSets:
            modelObject = self._objectFromID(dataSet[self._IDENTIFIER_KEY])
            if modelObject is not self._NO_OBJECT_MARKER:
                dataCopy = dataSet.copy()
                identifier = dataCopy.pop(self._IDENTIFIER_KEY)
                yield identifier, dataCopy


    def _coerceAll(self, inputs):
        """
        XXX
        """
        def associate(result, obj):
            return (obj, result)

        coerceDeferreds = []
        for obj, dataSet in inputs:
            oneCoerce = self._coerceSingleRepetition(dataSet)
            oneCoerce.addCallback(associate, obj)
            coerceDeferreds.append(oneCoerce)
        return gatherResults(coerceDeferreds)


    def coercer(self, dataSets):
        """
        Coerce all of the repetitions and sort them into creations, edits and
        deletions.

        @rtype: L{ListChanges}
        @return: An object describing all of the creations, modifications, and
            deletions represented by C{dataSets}.
        """
        # Xxx - This does a slightly complex (hey, it's like 20 lines, how
        # complex could it really be?) thing to figure out which elements are
        # newly created, which elements were edited, and which elements no
        # longer exist.  It might be simpler if the client kept track of this
        # and passed a three-tuple of lists (or whatever - some separate data
        # structures) to the server, so everything would be all figured out
        # already.  This would require the client
        # (Mantissa.LiveForm.RepeatableForm) to be more aware of what events
        # the user is triggering in the browser so that it could keep state for
        # adds/deletes/edits separately from DOM and widget objects.  This
        # would remove the need for RepeatedLiveFormWrapper.
        def makeSetter(identifier, values):
            def setter(defaultObject):
                self._idsToObjects[identifier] = defaultObject
                self._lastValues[identifier] = values
            return setter

        created = self._coerceAll(self._extractCreations(dataSets))
        edited = self._coerceAll(self._extractEdits(dataSets))

        coerceDeferred = gatherResults([created, edited])
        def cbCoerced((created, edited)):
            receivedIdentifiers = set()

            createObjects = []
            for (identifier, dataSet) in created:
                receivedIdentifiers.add(identifier)
                createObjects.append(
                    CreateObject(dataSet, makeSetter(identifier, dataSet)))

            editObjects = []
            for (identifier, dataSet) in edited:
                receivedIdentifiers.add(identifier)
                lastValues = self._lastValues[identifier]
                if dataSet != lastValues:
                    modelObject = self._objectFromID(identifier)
                    editObjects.append(EditObject(modelObject, dataSet))
                    self._lastValues[identifier] = dataSet

            deleted = []
            for identifier in set(self._idsToObjects) - receivedIdentifiers:
                existing = self._objectFromID(identifier)
                if existing is not self._NO_OBJECT_MARKER:
                    deleted.append(existing)
                self._idsToObjects.pop(identifier)

            return ListChanges(createObjects, editObjects, deleted)

        coerceDeferred.addCallback(cbCoerced)
        return coerceDeferred



MULTI_TEXT_INPUT = 'multi-text'

class ListParameter(record('name coercer count label description defaults '
                           'viewFactory',
                           label=None,
                           description=None,
                           defaults=None,
                           viewFactory=IParameterView)):

    type = MULTI_TEXT_INPUT
    def compact(self):
        """
        Don't do anything.
        """


    def fromInputs(self, inputs):
        """
        Extract the inputs associated with this parameter from the given
        dictionary and coerce them using C{self.coercer}.

        @type inputs: C{dict} mapping C{str} to C{list} of C{str}
        @param inputs: The contents of a form post, in the conventional
            structure.

        @rtype: L{Deferred}
        @return: A Deferred which will be called back with a list of the
            structured data associated with this parameter.
        """
        outputs = []
        for i in xrange(self.count):
            name = self.name + '_' + str(i)
            try:
                value = inputs[name][0]
            except KeyError:
                raise ConfigurationError(
                    "Missing value for field %d of %s" % (i, self.name))
            else:
                outputs.append(maybeDeferred(self.coercer, value))
        return gatherResults(outputs)



CHOICE_INPUT = 'choice'
MULTI_CHOICE_INPUT = 'multi-choice'


class Option(record('description value selected')):
    """
    A single choice for a L{ChoiceParameter}.
    """


class ChoiceParameter(record('name choices label description multiple '
                             'viewFactory',
                             label=None,
                             description="",
                             multiple=False,
                             viewFactory=IParameterView), _SelectiveCoercer):
    """
    A choice parameter, represented by a <select> element in HTML.

    @ivar choices: A sequence of L{Option} instances (deprecated: a sequence of
        three-tuples giving the attributes of L{Option} instances).

    @ivar multiple: C{True} if multiple choice selections are allowed

    @ivar viewFactory: A two-argument callable which returns an
        L{IParameterView} provider which will be used as the view for this
        parameter, if one can be provided.  It will be invoked with the
        parameter as the first argument and a default value as the second
        argument.  The default should be returned if no view can be provided
        for the given parameter.
    """
    def __init__(self, *a, **kw):
        ChoiceParameter.__bases__[0].__init__(self, *a, **kw)
        if self.choices and isinstance(self.choices[0], tuple):
            warnings.warn(
                "Pass a list of Option instances to ChoiceParameter, "
                "not a list of tuples.",
                category=DeprecationWarning,
                stacklevel=2)
            self.choices = [Option(*o) for o in self.choices]


    def type(self):
        if self.multiple:
            return MULTI_CHOICE_INPUT
        return CHOICE_INPUT
    type = property(type)


    def coercer(self, value):
        if self.multiple:
            return tuple(self.choices[int(v)].value for v in value)
        return self.choices[int(value)].value


    def compact(self):
        """
        Don't do anything.
        """


    def clone(self, choices):
        """
        Make a copy of this parameter, supply different choices.

        @param choices: A sequence of L{Option} instances.
        @type choices: C{list}

        @rtype: L{ChoiceParameter}
        """
        return self.__class__(
            self.name,
            choices,
            self.label,
            self.description,
            self.multiple,
            self.viewFactory)



class ConfigurationError(Exception):
    """
    User-specified configuration for a newly created Item was invalid or
    incomplete.
    """



class InvalidInput(Exception):
    """
    Data entered did not meet the requirements of the coercer.
    """



def _legacySpecialCases(form, patterns, parameter):
    """
    Create a view object for the given parameter.

    This function implements the remaining view construction logic which has
    not yet been converted to the C{viewFactory}-style expressed in
    L{_LiveFormMixin.form}.

    @type form: L{_LiveFormMixin}
    @param form: The form fragment which contains the given parameter.
    @type patterns: L{PatternDictionary}
    @type parameter: L{Parameter}, L{ChoiceParameter}, or L{ListParameter}.
    """
    p = patterns[parameter.type + '-input-container']

    if parameter.type == TEXTAREA_INPUT:
        p = dictFillSlots(p, dict(label=parameter.label,
                                  name=parameter.name,
                                  value=parameter.default or ''))
    elif parameter.type == MULTI_TEXT_INPUT:
        subInputs = list()

        for i in xrange(parameter.count):
            subInputs.append(dictFillSlots(patterns['input'],
                                dict(name=parameter.name + '_' + str(i),
                                     type='text',
                                     value=parameter.defaults[i])))

        p = dictFillSlots(p, dict(label=parameter.label or parameter.name,
                                  inputs=subInputs))

    else:
        if parameter.default is not None:
            value = parameter.default
        else:
            value = ''

        if parameter.type == CHECKBOX_INPUT and parameter.default:
            inputPattern = 'checked-checkbox-input'
        else:
            inputPattern = 'input'

        p = dictFillSlots(
            p, dict(label=parameter.label or parameter.name,
                    input=dictFillSlots(patterns[inputPattern],
                                        dict(name=parameter.name,
                                             type=parameter.type,
                                             value=value))))

    p(**{'class' : 'liveform_'+parameter.name})

    if parameter.description:
        description = patterns['description'].fillSlots(
                           'description', parameter.description)
    else:
        description = ''

    return dictFillSlots(
        patterns['parameter-input'],
        dict(input=p, description=description))



class _LiveFormMixin(record('callable parameters description',
                            description=None)):
    jsClass = _LIVEFORM_JS_CLASS

    subFormName = None

    fragmentName = 'liveform'
    compactFragmentName = 'liveform-compact'

    def __init__(self, *a, **k):
        super(_LiveFormMixin, self).__init__(*a, **k)
        if self.docFactory is None:
            # Give subclasses a chance to assign their own docFactory.
            self.docFactory = webtheme.getLoader(self.fragmentName)


    def compact(self):
        """
        Switch to the compact variant of the live form template.

        By default, this will simply create a loader for the
        C{self.compactFragmentName} template and compact all of this form's
        parameters.
        """
        self.docFactory = webtheme.getLoader(self.compactFragmentName)
        for param in self.parameters:
            param.compact()


    def getInitialArguments(self):
        if self.subFormName:
            subFormName = self.subFormName.decode('utf-8')
        else:
            subFormName = None
        return (subFormName,)


    def asSubForm(self, name):
        """
        Make a form suitable for nesting within another form (a subform) out
        of this top-level liveform.

        @param name: the name of the subform within its parent.
        @type name: C{unicode}

        @return: a subform.
        @rtype: L{LiveForm}
        """
        self.subFormName = name
        self.jsClass = _SUBFORM_JS_CLASS
        return self


    def _getDescription(self):
        descr = self.description
        if descr is None:
            descr = self.callable.__name__
        return descr


    def submitbutton(self, request, tag):
        """
        Render an INPUT element of type SUBMIT which will post this form to the
        server.
        """
        return tags.input(type='submit',
                          name='__submit__',
                          value=self._getDescription())
    page.renderer(submitbutton)


    def render_submitbutton(self, ctx, data):
        return self.submitbutton(inevow.IRequest(ctx), ctx.tag)


    def render_liveFragment(self, ctx, data):
        return self.liveElement(inevow.IRequest(ctx), ctx.tag)


    def form(self, request, tag):
        """
        Render the inputs for a form.

        @param tag: A tag with:
            - I{form} and I{description} slots
            - I{liveform} and I{subform} patterns, to fill the I{form} slot
                - An I{inputs} slot, to fill with parameter views
            - L{IParameterView.patternName}I{-input-container} patterns for
              each parameter type in C{self.parameters}
        """
        patterns = PatternDictionary(self.docFactory)
        inputs = []

        for parameter in self.parameters:
            view = parameter.viewFactory(parameter, None)
            if view is not None:
                view.setDefaultTemplate(
                    tag.onePattern(view.patternName + '-input-container'))
                setFragmentParent = getattr(view, 'setFragmentParent', None)
                if setFragmentParent is not None:
                    setFragmentParent(self)
                inputs.append(view)
            else:
                inputs.append(_legacySpecialCases(self, patterns, parameter))

        if self.subFormName is None:
            pattern = tag.onePattern('liveform')
        else:
            pattern = tag.onePattern('subform')

        return dictFillSlots(
            tag,
            dict(form=pattern.fillSlots('inputs', inputs),
                 description=self._getDescription()))
    page.renderer(form)


    def render_form(self, ctx, data):
        return self.form(inevow.IRequest(ctx), ctx.tag)


    def invoke(self, formPostEmulator):
        """
        Invoke my callable with input from the browser.

        @param formPostEmulator: a dict of lists of strings in a format like a
            cgi-module form post.
        """
        result = self.fromInputs(formPostEmulator)
        result.addCallback(lambda params: self.callable(**params))
        return result
    expose(invoke)


    def __call__(self, formPostEmulator):
        """
        B{Private} helper which passes through to L{invoke} to support legacy
        code passing L{LiveForm} instances to L{Parameter} instead of
        L{FormParameter}.  Do B{not} call this.
        """
        return self.invoke(formPostEmulator)


    def fromInputs(self, received):
        """
        Convert some random strings received from a browser into structured
        data, using a list of parameters.

        @param received: a dict of lists of strings, i.e. the canonical Python
            form of web form post.

        @rtype: L{Deferred}
        @return: A Deferred which will be called back with a dict mapping
            parameter names to coerced parameter values.
        """
        results = []
        for parameter in self.parameters:
            name = parameter.name.encode('ascii')
            d = maybeDeferred(parameter.fromInputs, received)
            d.addCallback(lambda value, name=name: (name, value))
            results.append(d)
        return gatherResults(results).addCallback(dict)



class LiveFormFragment(_LiveFormMixin, athena.LiveFragment):
    """
    DEPRECATED.

    @see LiveForm
    """



class LiveForm(_LiveFormMixin, athena.LiveElement):
    """
    A live form.

    Create with a callable and a list of L{Parameter}s which describe the form
    of the arguments which the callable will expect.

    @ivar callable: a callable that you can call

    @ivar parameters: a list of L{Parameter} objects describing the arguments
        which should be passed to C{callable}.
    """



class _ParameterViewMixin:
    """
    Base class providing common functionality for different parameter views.

    @type parameter: L{Parameter}
    """
    def __init__(self, parameter):
        """
        @type tag: L{nevow.stan.Tag}
        @param tag: The document template to use to render this view.
        """
        self.parameter = parameter


    def __eq__(self, other):
        """
        Define equality such other views which are instances of the same class
        as this view and which wrap the same L{Parameter} are considered equal
        to this one.
        """
        if isinstance(other, self.__class__):
            return self.parameter is other.parameter
        return False


    def __ne__(self, other):
        """
        Define inequality as the negation of equality.
        """
        return not self.__eq__(other)


    def setDefaultTemplate(self, tag):
        """
        Use the given default template.
        """
        self.docFactory = stan(tag)


    def name(self, request, tag):
        """
        Render the name of the wrapped L{Parameter} or L{ChoiceParameter} instance.
        """
        return tag[self.parameter.name]
    renderer(name)


    def label(self, request, tag):
        """
        Render the label of the wrapped L{Parameter} or L{ChoiceParameter} instance.
        """
        if self.parameter.label:
            tag[self.parameter.label]
        return tag
    renderer(label)


    def description(self, request, tag):
        """
        Render the description of the wrapped L{Parameter} instance.
        """
        if self.parameter.description is not None:
            tag[self.parameter.description]
        return tag
    renderer(description)



class RepeatedLiveFormWrapper(athena.LiveElement):
    """
    A wrapper around a L{LiveForm} which has been repeated via
    L{ListChangeParameter.asLiveForm}.

    @ivar liveForm: The repeated liveform.
    @type liveForm: L{LiveForm}

    @ivar identifier: An integer identifying this repetition.
    @type identifier: C{int}

    @ivar removable: Whether this repetition can be unrepeated/removed.
    @type removable: C{bool}
    """
    fragmentName = 'repeated-liveform'
    jsClass = u'Mantissa.LiveForm.RepeatedLiveFormWrapper'

    def __init__(self, liveForm, identifier, removable=True):
        athena.LiveElement.__init__(self)
        self.liveForm = liveForm
        self.identifier = identifier
        self.removable = removable


    def getInitialArguments(self):
        """
        Include the name of the form we're wrapping, and our original values.
        """
        return (self.liveForm.subFormName.decode('utf-8'), self.identifier)


    def realForm(self, req, tag):
        """
        Render L{liveForm}.
        """
        self.liveForm.setFragmentParent(self)
        return self.liveForm
    page.renderer(realForm)


    def removeLink(self, req, tag):
        """
        Render C{tag} if L{removable} is C{True}, otherwise return the
        empty string.
        """
        if self.removable:
            return tag
        return ''
    page.renderer(removeLink)



class _TextLikeParameterView(_ParameterViewMixin, Element):
    """
    View definition base class for L{Parameter} instances which are simple text
    inputs.
    """
    def default(self, request, tag):
        """
        Render the initial value of the wrapped L{Parameter} instance.
        """
        if self.parameter.default is not None:
            tag[self.parameter.default]
        return tag
    renderer(default)



class TextParameterView(_TextLikeParameterView):
    """
    View definition for L{Parameter} instances with type of C{TEXT_INPUT}
    """
    implements(IParameterView)
    patternName = 'text'



class PasswordParameterView(_TextLikeParameterView):
    """
    View definition for L{Parameter} instances with type of C{PASSWORD_INPUT}
    """
    implements(IParameterView)
    patternName = 'password'



class OptionView(Element):
    """
    View definition for a single choice of a L{ChoiceParameter}.

    @type option: L{Option}
    """
    def __init__(self, index, option, tag):
        self._index = index
        self.option = option
        self.docFactory = stan(tag)


    def __eq__(self, other):
        """
        Define equality such other L{OptionView} instances which wrap the same
        L{Option} are considered equal to this one.
        """
        if isinstance(other, OptionView):
            return self.option is other.option
        return False


    def __ne__(self, other):
        """
        Define inequality as the negation of equality.
        """
        return not self.__eq__(other)


    def description(self, request, tag):
        """
        Render the description of the wrapped L{Option} instance.
        """
        return tag[self.option.description]
    renderer(description)


    def value(self, request, tag):
        """
        Render the value of the wrapped L{Option} instance.
        """
        return tag[self.option.value]
    renderer(value)


    def index(self, request, tag):
        """
        Render the index specified to C{__init__}.
        """
        return tag[self._index]
    renderer(index)


    def selected(self, request, tag):
        """
        Render a selected attribute on the given tag if the wrapped L{Option}
        instance is selected.
        """
        if self.option.selected:
            tag(selected='selected')
        return tag
    renderer(selected)



def _textParameterToView(parameter):
    """
    Return a L{TextParameterView} adapter for C{TEXT_INPUT}, C{PASSWORD_INPUT},
    and C{FORM_INPUT} L{Parameter} instances.
    """
    if parameter.type == TEXT_INPUT:
        return TextParameterView(parameter)
    if parameter.type == PASSWORD_INPUT:
        return PasswordParameterView(parameter)
    if parameter.type == FORM_INPUT:
        return FormInputParameterView(parameter)
    return None

registerAdapter(_textParameterToView, Parameter, IParameterView)


class ChoiceParameterView(_ParameterViewMixin, Element):
    """
    View definition for L{Parameter} instances with type of C{CHOICE_INPUT}.
    """
    implements(IParameterView)
    patternName = 'choice'

    def multiple(self, request, tag):
        """
        Render a I{multiple} attribute on the given tag if the wrapped
        L{ChoiceParameter} instance allows multiple selection.
        """
        if self.parameter.multiple:
            tag(multiple='multiple')
        return tag
    renderer(multiple)


    def options(self, request, tag):
        """
        Render each of the options of the wrapped L{ChoiceParameter} instance.
        """
        option = tag.patternGenerator('option')
        return tag[[
                OptionView(index, o, option())
                for (index, o)
                in enumerate(self.parameter.choices)]]
    renderer(options)

registerAdapter(ChoiceParameterView, ChoiceParameter, IParameterView)



class ListChangeParameterView(_ParameterViewMixin, athena.LiveElement):
    """
    L{IParameterView} adapter for L{ListChangeParameter}.

    @ivar parameter: the parameter being viewed.
    @type parameter: L{ListChangeParameter}
    """
    jsClass = u'Mantissa.LiveForm.RepeatableForm'
    patternName = 'repeatable-form'

    def __init__(self, parameter):
        self.parameter = parameter
        athena.LiveElement.__init__(self)


    def getInitialArguments(self):
        """
        Pass the name of our parameter to the client.
        """
        return (self.parameter.name,)


    def forms(self, req, tag):
        """
        Make and return some forms, using L{self.parameter.getInitialLiveForms}.

        @return: some subforms.
        @rtype: C{list} of L{LiveForm}
        """
        liveForms = self.parameter.getInitialLiveForms()
        for liveForm in liveForms:
            liveForm.setFragmentParent(self)
        return liveForms
    page.renderer(forms)


    def repeatForm(self):
        """
        Make and return a form, using L{self.parameter.asLiveForm}.

        @return: a subform.
        @rtype: L{LiveForm}
        """
        liveForm = self.parameter.asLiveForm()
        liveForm.setFragmentParent(self)
        return liveForm
    athena.expose(repeatForm)


    def repeater(self, req, tag):
        """
        Render some UI for repeating our form.
        """
        repeater = inevow.IQ(self.docFactory).onePattern('repeater')
        return repeater.fillSlots(
            'object-description', self.parameter.modelObjectDescription)
    page.renderer(repeater)

registerAdapter(ListChangeParameterView, ListChangeParameter, IParameterView)



class FormParameterView(_ParameterViewMixin, athena.LiveElement):
    """
    L{IParameterView} adapter for L{FormParameter}.

    @ivar parameter: the parameter being viewed.
    @type parameter: L{FormParameter}
    """
    implements(IParameterView)
    patternName = 'form'

    def __init__(self, parameter):
        _ParameterViewMixin.__init__(self, parameter)
        athena.LiveElement.__init__(self)


    def input(self, request, tag):
        """
        Add the wrapped form, as a subform, as a child of the given tag.
        """
        subform = self.parameter.form.asSubForm(self.parameter.name)
        subform.setFragmentParent(self)
        return tag[subform]
    renderer(input)

registerAdapter(FormParameterView, FormParameter, IParameterView)



class FormInputParameterView(_ParameterViewMixin, athena.LiveElement):
    """
    L{IParameterView} adapter for C{FORM_INPUT} L{Parameter}s.

    @ivar parameter: the parameter being viewed.
    @type parameter: L{Parameter}
    """
    implements(IParameterView)
    patternName = 'form'

    def __init__(self, parameter):
        _ParameterViewMixin.__init__(self, parameter)
        athena.LiveElement.__init__(self)


    def input(self, request, tag):
        """
        Add the wrapped form, as a subform, as a child of the given tag.
        """
        subform = self.parameter.coercer.asSubForm(self.parameter.name)
        subform.setFragmentParent(self)
        return tag[subform]
    renderer(input)
