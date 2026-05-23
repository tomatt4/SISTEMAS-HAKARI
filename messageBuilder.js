const {
    ContainerBuilder,
    TextDisplayBuilder,
    SeparatorBuilder,
    MessageFlags
} = require("discord.js");

function createMessage({
    title,
    description,
    fields = [],
    footer = null
}) {

    const container = new ContainerBuilder();

    // Título
    container.addTextDisplayComponents(
        new TextDisplayBuilder()
            .setContent(`# ${title}`)
    );

    // Linha
    container.addSeparatorComponents(
        new SeparatorBuilder()
    );

    // Descrição
    if (description) {

        container.addTextDisplayComponents(
            new TextDisplayBuilder()
                .setContent(description)
        );
    }

    // Campos
    if (fields.length > 0) {

        const formattedFields = fields
            .map(field =>
                `### ${field.name}\n${field.value}`
            )
            .join("\n\n");

        container.addTextDisplayComponents(
            new TextDisplayBuilder()
                .setContent(formattedFields)
        );
    }

    // Footer
    if (footer) {

        container.addSeparatorComponents(
            new SeparatorBuilder()
        );

        container.addTextDisplayComponents(
            new TextDisplayBuilder()
                .setContent(`-# ${footer}`)
        );
    }

    return {
        flags: MessageFlags.IsComponentsV2,
        components: [container]
    };
}

module.exports = {
    createMessage
};