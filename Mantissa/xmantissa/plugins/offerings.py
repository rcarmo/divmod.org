from xmantissa import people, offering, website

peopleOffering = offering.Offering(
    name=u'People',
    description=u'Basic organizer and addressbook support.',

    siteRequirements=((None, website.WebSite),),
    appPowerups=(),
    installablePowerups = [("People", "Organizer and Address Book", people.AddPerson)],
    loginInterfaces=(),
    themes=())

