#include <stdio.h>
#include <unistd.h>
#include <inttypes.h>
#include <fcntl.h>

#include <drm.h>
#include <xf86drmMode.h>

int main(int argc, char* argv[]) {
	drmModeRes *resources = NULL;
	drmModeConnector *connector = NULL;
	int i, ret = 0;

	int drm_fd = open("/dev/dri/card0", O_RDWR);

	resources = drmModeGetResources(drm_fd);
	if (!resources) {
		fprintf(stderr, "drmModeGetResources failed\n");
		ret = 1;
		goto error;
	}

	for (i = 0; i < resources->count_connectors; ++i) {
		connector = drmModeGetConnector(drm_fd, resources->connectors[i]);
		if (connector == NULL)
			continue;

		if (connector->connection == DRM_MODE_CONNECTED &&
			 connector->count_modes > 0)
			break;

		drmModeFreeConnector(connector);
	}

	if (i == resources->count_connectors) {
		fprintf(stderr, "No currently active connector found.\n");
		ret = 2;
		goto error;
	}

	for (i = 0; i < connector->count_modes; ++i) {
		printf(
			"%dx%d%s@%d\n",
			connector->modes[i].hdisplay,
			connector->modes[i].vdisplay,
			(connector->modes[i].flags & DRM_MODE_FLAG_INTERLACE) ? "i" : "",
			connector->modes[i].vrefresh
		);
	}

error:
	if(connector) drmModeFreeConnector(connector);
	if(resources) drmModeFreeResources(resources);
	close(drm_fd);
	return ret;
}
