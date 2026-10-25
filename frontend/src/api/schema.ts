// Generated from contract/openapi.json by `npm run generate:api`. Do not edit by hand.

export interface paths {
    "/health": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Check that the API is up */
        get: operations["getHealth"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/collections": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List collections as a tree
         * @description Return all collections as a tree; siblings are sorted by name, case-insensitively.
         */
        get: operations["listCollections"];
        put?: never;
        /** Create a collection */
        post: operations["createCollection"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/collections/{collection_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /**
         * Delete an empty collection
         * @description Delete an empty collection. A collection that still has child collections or notes is not deleted: the request is rejected with 409 Conflict. Unknown ids return 404.
         */
        delete: operations["deleteCollection"];
        options?: never;
        head?: never;
        /**
         * Rename or move a collection
         * @description Rename and/or move a collection. Omit `parent_id` to stay put; `null` moves to top level.
         */
        patch: operations["updateCollection"];
        trace?: never;
    };
    "/tags": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List tags */
        get: operations["listTags"];
        put?: never;
        /** Create a tag */
        post: operations["createTag"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/tags/{tag_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Rename a tag */
        patch: operations["renameTag"];
        trace?: never;
    };
    "/notes": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create a note */
        post: operations["createNote"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/notes/{note_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get a note */
        get: operations["getNote"];
        put?: never;
        post?: never;
        /** Delete a note */
        delete: operations["deleteNote"];
        options?: never;
        head?: never;
        /** Update part of a note */
        patch: operations["updateNote"];
        trace?: never;
    };
    "/timeline": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List notes newest first, one page at a time */
        get: operations["getTimeline"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/resurface": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Pick up to three older notes to revisit */
        get: operations["getResurfacedNotes"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/notes/{note_id}/resurfaced": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Record that a note was shown */
        post: operations["markNoteResurfaced"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /**
         * ChecklistItemIn
         * @description A checklist item as sent by the client; its position is its index in the list.
         */
        ChecklistItemIn: {
            /** Text */
            text: string;
            /**
             * Done
             * @default false
             */
            done: boolean;
        };
        /** ChecklistItemOut */
        ChecklistItemOut: {
            /** Text */
            text: string;
            /** Done */
            done: boolean;
            /** Position */
            position: number;
        };
        /** CollectionCreate */
        CollectionCreate: {
            /** Name */
            name: string;
            /** Parent Id */
            parent_id?: string | null;
        };
        /** CollectionOut */
        CollectionOut: {
            /** Id */
            id: string;
            /** Name */
            name: string;
            /** Parent Id */
            parent_id: string | null;
        };
        /**
         * CollectionTreeNode
         * @description Documents the `GET /collections` node shape in OpenAPI.
         *
         *     The endpoint itself returns `CollectionTree` dicts encoded by `dump_tree_json`, because
         *     Pydantic's recursive serializer fails on deep (about 99+ levels) trees.
         */
        CollectionTreeNode: {
            /** Id */
            id: string;
            /** Name */
            name: string;
            /** Parent Id */
            parent_id: string | null;
            /** Children */
            children: components["schemas"]["CollectionTreeNode"][];
        };
        /**
         * CollectionUpdate
         * @description Rename and/or move; an omitted `parent_id` means "don't move", `null` means top level.
         */
        CollectionUpdate: {
            /** Name */
            name?: string | null;
            /** Parent Id */
            parent_id?: string | null;
        };
        /**
         * Error
         * @description The body of every error response. `errors` is non-empty only for `validation_error`.
         */
        Error: {
            /** Code */
            code: string;
            /** Message */
            message: string;
            /** Errors */
            errors: components["schemas"]["ErrorItem"][];
        };
        /**
         * ErrorItem
         * @description One invalid input: where it was (`location`), which field (`field`, dot-joined) and why.
         */
        ErrorItem: {
            /**
             * Location
             * @enum {string}
             */
            location: "body" | "query" | "path";
            /** Field */
            field: string | null;
            /** Message */
            message: string;
        };
        /** Health */
        Health: {
            /**
             * Status
             * @constant
             */
            status: "ok";
        };
        /** IdeaNoteCreate */
        IdeaNoteCreate: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "idea";
            /** Body */
            body: string;
            /** Collection Id */
            collection_id: string;
            /** Tag Ids */
            tag_ids?: string[];
        };
        /** IdeaNoteOut */
        IdeaNoteOut: {
            /** Id */
            id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "idea";
            /** Body */
            body: string;
            /** Collection Id */
            collection_id: string;
            /** Tag Ids */
            tag_ids: string[];
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Last Resurfaced At */
            last_resurfaced_at: string | null;
            /** Resurface Count */
            resurface_count: number;
        };
        /** JournalNoteCreate */
        JournalNoteCreate: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "journal";
            /** Body */
            body: string;
            /** Collection Id */
            collection_id: string;
            /** Tag Ids */
            tag_ids?: string[];
            /** Entry Date */
            entry_date?: string | null;
            /** Mood */
            mood?: string | null;
            /** Prompt */
            prompt?: string | null;
            /** Is Retrospective */
            is_retrospective?: boolean | null;
            /** Period */
            period?: ("weekly" | "monthly") | null;
        };
        /** JournalNoteOut */
        JournalNoteOut: {
            /** Id */
            id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "journal";
            /** Body */
            body: string;
            /** Collection Id */
            collection_id: string;
            /** Tag Ids */
            tag_ids: string[];
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Last Resurfaced At */
            last_resurfaced_at: string | null;
            /** Resurface Count */
            resurface_count: number;
            /**
             * Entry Date
             * Format: date-time
             */
            entry_date: string;
            /** Mood */
            mood: string | null;
            /** Prompt */
            prompt: string | null;
            /** Is Retrospective */
            is_retrospective: boolean;
            /** Period */
            period: ("weekly" | "monthly") | null;
        };
        /** MemoryNoteCreate */
        MemoryNoteCreate: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "memory";
            /** Body */
            body: string;
            /** Collection Id */
            collection_id: string;
            /** Tag Ids */
            tag_ids?: string[];
            /** When */
            when?: string | null;
            /** Where */
            where?: string | null;
        };
        /** MemoryNoteOut */
        MemoryNoteOut: {
            /** Id */
            id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "memory";
            /** Body */
            body: string;
            /** Collection Id */
            collection_id: string;
            /** Tag Ids */
            tag_ids: string[];
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Last Resurfaced At */
            last_resurfaced_at: string | null;
            /** Resurface Count */
            resurface_count: number;
            /** When */
            when: string | null;
            /** Where */
            where: string | null;
        };
        /**
         * NoteUpdate
         * @description Partial update; omitted fields keep their value.
         *
         *     Explicit `null` is rejected for shared and required fields, and clears optional Type fields.
         *     Type fields are listed for every Type here; the service rejects those that don't belong to the note.
         */
        NoteUpdate: {
            /** Type */
            type?: ("journal" | "idea" | "reference" | "plan" | "memory") | null;
            /** Body */
            body?: string | null;
            /** Collection Id */
            collection_id?: string | null;
            /** Tag Ids */
            tag_ids?: string[] | null;
            /** Entry Date */
            entry_date?: string | null;
            /** Mood */
            mood?: string | null;
            /** Prompt */
            prompt?: string | null;
            /** Is Retrospective */
            is_retrospective?: boolean | null;
            /** Period */
            period?: ("weekly" | "monthly") | null;
            /** Sub Kind */
            sub_kind?: ("written" | "visual" | "audio") | null;
            /** Link */
            link?: string | null;
            /** Target Date */
            target_date?: string | null;
            /** State */
            state?: ("not_started" | "in_progress" | "done" | "abandoned") | null;
            /** Checklist */
            checklist?: components["schemas"]["ChecklistItemIn"][] | null;
            /** When */
            when?: string | null;
            /** Where */
            where?: string | null;
        };
        /** PlanNoteCreate */
        PlanNoteCreate: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "plan";
            /** Body */
            body: string;
            /** Collection Id */
            collection_id: string;
            /** Tag Ids */
            tag_ids?: string[];
            /** Target Date */
            target_date?: string | null;
            /** State */
            state?: ("not_started" | "in_progress" | "done" | "abandoned") | null;
            /** Checklist */
            checklist?: components["schemas"]["ChecklistItemIn"][] | null;
        };
        /** PlanNoteOut */
        PlanNoteOut: {
            /** Id */
            id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "plan";
            /** Body */
            body: string;
            /** Collection Id */
            collection_id: string;
            /** Tag Ids */
            tag_ids: string[];
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Last Resurfaced At */
            last_resurfaced_at: string | null;
            /** Resurface Count */
            resurface_count: number;
            /** Target Date */
            target_date: string | null;
            /**
             * State
             * @enum {string}
             */
            state: "not_started" | "in_progress" | "done" | "abandoned";
            /** Checklist */
            checklist: components["schemas"]["ChecklistItemOut"][];
        };
        /** ReferenceNoteCreate */
        ReferenceNoteCreate: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "reference";
            /** Body */
            body: string;
            /** Collection Id */
            collection_id: string;
            /** Tag Ids */
            tag_ids?: string[];
            /** Sub Kind */
            sub_kind?: ("written" | "visual" | "audio") | null;
            /** Link */
            link?: string | null;
        };
        /** ReferenceNoteOut */
        ReferenceNoteOut: {
            /** Id */
            id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "reference";
            /** Body */
            body: string;
            /** Collection Id */
            collection_id: string;
            /** Tag Ids */
            tag_ids: string[];
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Last Resurfaced At */
            last_resurfaced_at: string | null;
            /** Resurface Count */
            resurface_count: number;
            /**
             * Sub Kind
             * @enum {string}
             */
            sub_kind: "written" | "visual" | "audio";
            /** Link */
            link: string | null;
        };
        /** ResurfaceOut */
        ResurfaceOut: {
            /** Items */
            items: (components["schemas"]["JournalNoteOut"] | components["schemas"]["IdeaNoteOut"] | components["schemas"]["ReferenceNoteOut"] | components["schemas"]["PlanNoteOut"] | components["schemas"]["MemoryNoteOut"])[];
        };
        /** TagCreate */
        TagCreate: {
            /** Name */
            name: string;
        };
        /** TagOut */
        TagOut: {
            /** Id */
            id: string;
            /** Name */
            name: string;
        };
        /** TagUpdate */
        TagUpdate: {
            /** Name */
            name: string;
        };
        /** TimelinePageOut */
        TimelinePageOut: {
            /** Items */
            items: (components["schemas"]["JournalNoteOut"] | components["schemas"]["IdeaNoteOut"] | components["schemas"]["ReferenceNoteOut"] | components["schemas"]["PlanNoteOut"] | components["schemas"]["MemoryNoteOut"])[];
            /** Next Cursor */
            next_cursor: string | null;
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    getHealth: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Health"];
                };
            };
        };
    };
    listCollections: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CollectionTreeNode"][];
                };
            };
        };
    };
    createCollection: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CollectionCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CollectionOut"];
                };
            };
            /** @description Conflicts with existing data */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Invalid input (`validation_error`) or a broken business rule */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    deleteCollection: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                collection_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Not found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Conflicts with existing data */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Invalid input (`validation_error`) or a broken business rule */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    updateCollection: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                collection_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CollectionUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CollectionOut"];
                };
            };
            /** @description The request breaks a rule (e.g. a collection cycle) */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Not found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Conflicts with existing data */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Invalid input (`validation_error`) or a broken business rule */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    listTags: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TagOut"][];
                };
            };
        };
    };
    createTag: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TagCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TagOut"];
                };
            };
            /** @description Conflicts with existing data */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Invalid input (`validation_error`) or a broken business rule */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    renameTag: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                tag_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TagUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TagOut"];
                };
            };
            /** @description Not found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Conflicts with existing data */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Invalid input (`validation_error`) or a broken business rule */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    createNote: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["JournalNoteCreate"] | components["schemas"]["IdeaNoteCreate"] | components["schemas"]["ReferenceNoteCreate"] | components["schemas"]["PlanNoteCreate"] | components["schemas"]["MemoryNoteCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["JournalNoteOut"] | components["schemas"]["IdeaNoteOut"] | components["schemas"]["ReferenceNoteOut"] | components["schemas"]["PlanNoteOut"] | components["schemas"]["MemoryNoteOut"];
                };
            };
            /** @description Invalid input (`validation_error`) or a broken business rule */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    getNote: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                note_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["JournalNoteOut"] | components["schemas"]["IdeaNoteOut"] | components["schemas"]["ReferenceNoteOut"] | components["schemas"]["PlanNoteOut"] | components["schemas"]["MemoryNoteOut"];
                };
            };
            /** @description Not found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Invalid input (`validation_error`) or a broken business rule */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    deleteNote: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                note_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Not found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Invalid input (`validation_error`) or a broken business rule */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    updateNote: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                note_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["NoteUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["JournalNoteOut"] | components["schemas"]["IdeaNoteOut"] | components["schemas"]["ReferenceNoteOut"] | components["schemas"]["PlanNoteOut"] | components["schemas"]["MemoryNoteOut"];
                };
            };
            /** @description Not found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Invalid input (`validation_error`) or a broken business rule */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    getTimeline: {
        parameters: {
            query?: {
                /** @description Page size, 1 to 100. */
                limit?: number;
                /** @description `next_cursor` from the previous page; only valid with the same filters. */
                cursor?: string | null;
                /** @description Only notes in this collection. */
                collection_id?: string | null;
                /** @description With `collection_id`: also notes in all nested sub-collections. */
                include_descendants?: boolean;
                /** @description Only notes of this Type. */
                type?: ("journal" | "idea" | "reference" | "plan" | "memory") | null;
                /** @description Only notes that have this tag. */
                tag_id?: string | null;
                /** @description Only notes without tags; cannot be combined with `tag_id`. */
                untagged?: boolean;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TimelinePageOut"];
                };
            };
            /** @description Invalid input (`validation_error`) or a broken business rule */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    getResurfacedNotes: {
        parameters: {
            query?: {
                /** @description Note ids to avoid, e.g. the previously shown set. Repeatable. */
                exclude?: string[] | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ResurfaceOut"];
                };
            };
            /** @description Invalid input (`validation_error`) or a broken business rule */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    markNoteResurfaced: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                note_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["JournalNoteOut"] | components["schemas"]["IdeaNoteOut"] | components["schemas"]["ReferenceNoteOut"] | components["schemas"]["PlanNoteOut"] | components["schemas"]["MemoryNoteOut"];
                };
            };
            /** @description Not found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Invalid input (`validation_error`) or a broken business rule */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
}
