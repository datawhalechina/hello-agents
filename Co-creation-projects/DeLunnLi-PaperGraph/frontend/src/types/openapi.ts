export interface components {
    schemas: {
        Author: {
            name: string;
            affiliation?: string | null;
            email?: string | null;
            orcid?: string | null;
            db_id?: number | null;
        },
        LibraryCategoriesResponse: {
            success: boolean;
            store_root: string;
            folders?: components["schemas"]["LibraryCategoryFolder"][];
        },
        LibraryCategoryChild: {
            category: string;
            label: string;
            folder: string;
            count: number;
        },
        LibraryCategoryFolder: {
            category: string;
            folder: string;
            count: number;
            children?: components["schemas"]["LibraryCategoryChild"][];
        },
        Paper: {
            id?: number | null;
            title: string;
            authors: components["schemas"]["Author"][];
            abstract?: string | null;
            doi?: string | null;
            pmid?: string | null;
            arxiv_id?: string | null;
            pmc_id?: string | null;
            journal?: string | null;
            venue_type?: string | null;
            year?: number | null;
            volume?: string | null;
            issue?: string | null;
            pages?: string | null;
            publisher?: string | null;
            pdf_url?: string | null;
            source_url?: string | null;
            local_pdf_path?: string | null;
            keywords: string[];
            mesh_terms: string[];
            references: string[];
            citations: number;
            source: components["schemas"]["PaperSource"];
            relevance_score: number;
            notes?: string | null;
            tags: string[];
            category?: string | null;
            rating?: number | null;
            read_status: components["schemas"]["ReadStatus"];
            importance: string;
            created_at?: string | null;
            updated_at?: string | null;
        },
        PapersResponse: {
            success: boolean;
            total: number;
            papers: components["schemas"]["Paper"][];
            message?: string | null;
        },
        SavePapersResponse: {
            success: boolean;
            added: number;
            updated: number;
            ids: number[];
            pdf_downloaded: number;
            llm_classified: number;
            message?: string | null;
        },
        PaperSource: "pubmed" | "arxiv" | "crossref" | "semantic_scholar" | "openalex" | "dblp" | "tavily" | "unknown";
        ReadStatus: "unread" | "reading" | "read";
    }
}