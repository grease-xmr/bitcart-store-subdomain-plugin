<template>
  <span>
    <v-tooltip bottom>
      <template #activator="{ on, attrs }">
        <v-icon
          small
          class="mr-2"
          v-bind="attrs"
          v-on="on"
          @click="openDialog"
        >
          mdi-link-variant
        </v-icon>
      </template>
      <span>{{ currentSlug ? 'Edit subdomain' : 'Set subdomain' }}</span>
    </v-tooltip>

    <v-dialog v-model="dialog" max-width="500px" persistent>
      <v-card>
        <v-card-title>
          <span class="text-h5">Store Subdomain</span>
        </v-card-title>

        <v-card-text>
          <v-container>
            <v-row>
              <v-col cols="12">
                <p v-if="currentSlug" class="mb-4">
                  Current subdomain: <strong>{{ currentSlug }}</strong>
                </p>
                <p v-else class="mb-4 text--secondary">
                  No subdomain configured for this store.
                </p>
              </v-col>
            </v-row>
            <v-row>
              <v-col cols="12">
                <v-text-field
                  v-model="slug"
                  label="Subdomain slug"
                  :rules="slugRules"
                  :error-messages="errorMessage"
                  hint="3-63 characters, lowercase letters, numbers, and hyphens only"
                  persistent-hint
                  outlined
                  dense
                  @input="errorMessage = ''"
                />
              </v-col>
            </v-row>
          </v-container>
        </v-card-text>

        <v-card-actions>
          <v-btn
            v-if="currentSlug"
            color="error"
            text
            :loading="deleting"
            @click="deleteSlug"
          >
            Remove
          </v-btn>
          <v-spacer />
          <v-btn text @click="closeDialog">Cancel</v-btn>
          <v-btn
            color="primary"
            :loading="saving"
            :disabled="!isValid"
            @click="saveSlug"
          >
            Save
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="snackbar" :color="snackbarColor" :timeout="3000">
      {{ snackbarText }}
    </v-snackbar>
  </span>
</template>

<script>
export default {
  name: 'StoreSlugAction',
  props: {
    item: {
      type: Object,
      required: true,
    },
  },
  data() {
    return {
      dialog: false,
      slug: '',
      currentSlug: null,
      saving: false,
      deleting: false,
      errorMessage: '',
      snackbar: false,
      snackbarText: '',
      snackbarColor: 'success',
      slugRules: [
        (v) => !v || v.length >= 3 || 'Slug must be at least 3 characters',
        (v) => !v || v.length <= 63 || 'Slug must be at most 63 characters',
        (v) =>
          !v ||
          /^[a-z0-9]([a-z0-9-]*[a-z0-9])?$/.test(v) ||
          'Must start and end with alphanumeric, may contain hyphens',
        (v) => !v || !v.includes('--') || 'Consecutive hyphens not allowed',
      ],
    }
  },
  computed: {
    isValid() {
      if (!this.slug) return false
      return this.slugRules.every((rule) => rule(this.slug) === true)
    },
  },
  methods: {
    async openDialog() {
      this.dialog = true
      this.errorMessage = ''
      this.currentSlug = this.item.metadata?.['store-subdomains:slug'] || null
      this.slug = this.currentSlug || ''
    },
    closeDialog() {
      this.dialog = false
      this.slug = ''
      this.errorMessage = ''
    },
    async saveSlug() {
      if (!this.isValid) return

      this.saving = true
      this.errorMessage = ''

      try {
        const response = await this.$axios.patch(
          `/stores/${this.item.id}/slug`,
          { slug: this.slug.toLowerCase() }
        )
        this.currentSlug = response.data.slug
        this.item.metadata = this.item.metadata || {}
        this.item.metadata['store-subdomains:slug'] = response.data.slug
        this.showSnackbar('Subdomain saved successfully', 'success')
        this.closeDialog()
      } catch (error) {
        const message =
          error.response?.data?.detail || 'Failed to save subdomain'
        this.errorMessage = message
      } finally {
        this.saving = false
      }
    },
    async deleteSlug() {
      this.deleting = true
      this.errorMessage = ''

      try {
        await this.$axios.delete(`/stores/${this.item.id}/slug`)
        this.currentSlug = null
        if (this.item.metadata) {
          delete this.item.metadata['store-subdomains:slug']
        }
        this.showSnackbar('Subdomain removed', 'success')
        this.closeDialog()
      } catch (error) {
        const message =
          error.response?.data?.detail || 'Failed to remove subdomain'
        this.errorMessage = message
      } finally {
        this.deleting = false
      }
    },
    showSnackbar(text, color) {
      this.snackbarText = text
      this.snackbarColor = color
      this.snackbar = true
    },
  },
}
</script>
