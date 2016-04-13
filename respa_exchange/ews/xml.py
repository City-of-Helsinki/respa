from lxml.builder import ElementMaker

NAMESPACES = {
    'm': 'http://schemas.microsoft.com/exchange/services/2006/messages',
    't': 'http://schemas.microsoft.com/exchange/services/2006/types',
    's': 'http://schemas.xmlsoap.org/soap/envelope/',
}
M = ElementMaker(namespace=NAMESPACES['m'], nsmap=NAMESPACES)
T = ElementMaker(namespace=NAMESPACES['t'], nsmap=NAMESPACES)
S = ElementMaker(namespace=NAMESPACES['s'], nsmap=NAMESPACES)
