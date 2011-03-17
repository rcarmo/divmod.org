// import Quotient
// import Quotient.Common
// import LightBox

Quotient.Gallery.Controller = Nevow.Athena.Widget.subclass("Quotient.Gallery.Controller");

Quotient.Gallery.Controller.methods(
    function __init__(self, node) {
        Quotient.Gallery.Controller.upcall(self, "__init__", node);
        self.images = self.nodeByAttribute("class", "images");
        self.paginationLinks = self.nodeByAttribute("class", "pagination-links");
    },

    function setGalleryState(self, data) {
        self.images.innerHTML = data[0];
        self.paginationLinks.innerHTML = data[1];
        initLightbox();
    },

    function prevPage(self) {
        self.callRemote("prevPage").addCallback(
            function(gs) { self.setGalleryState(gs) });
    },

    function nextPage(self) {
        self.callRemote("nextPage").addCallback(
            function(gs) { self.setGalleryState(gs) });
    });
