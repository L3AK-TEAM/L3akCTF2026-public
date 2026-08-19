export default {
    async fetch( request ) {
        const { post_id, author_name, author_id, viewer_id, viewer_name, like_ids, is_private } = await request.json();

        let flag = "nothing to see here...";

        if ( author_id === viewer_id && viewer_name === author_name ) {
            flag = "L3AK{workerd_pronounced_worker_dee_is_a_javascript_wasm_server_runtime_based_on_the_same_code_that_powers_cloudflare_workers}"
        }

        return new Response(
            "<main style=\"font: 16px system-ui; padding: 2rem\">" +
            "<h1>" + author_name + "'s secret storage</h1>" +
            "<p>" + flag + "</p></main>",
            { headers: { "Content-Type": "text/html; charset=utf-8" } },
        );
    },
};