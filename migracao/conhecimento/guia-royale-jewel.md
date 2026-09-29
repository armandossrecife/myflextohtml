# Guia de migração: Adobe Flex (MX/Spark) → Apache Royale 0.9.12 (Jewel)

Os agentes da migração usam este guia como referência. Todos os padrões abaixo foram
**compilados e testados** com o Apache Royale 0.9.12 (alvo `JSRoyale`) e o tema Jewel.

## 1. Como o Royale compila

- O compilador `mxmlc` do Royale lê MXML e AS3 e gera JavaScript, CSS e `index.html`.
  O resultado final fica em `bin/js-release/`.
- **Não existe Flash Player.** Qualquer API `flash.*` e qualquer classe `mx.*` ou `spark.*` do Flex
  deixam de existir e precisam ser trocadas.
- Comando usado pelo pipeline (você não precisa rodá-lo à mão):
  `mxmlc -targets=JSRoyale -theme=<JewelTheme>/defaults.css -source-path=src -js-output=. -js-dynamic-access-unknown-members=true src/<Principal>.mxml`

## 2. Esqueleto obrigatório da aplicação

```xml
<?xml version="1.0" encoding="utf-8"?>
<j:Application xmlns:fx="http://ns.adobe.com/mxml/2009"
               xmlns:j="library://ns.apache.org/royale/jewel"
               xmlns:js="library://ns.apache.org/royale/basic"
               xmlns:html="library://ns.apache.org/royale/html"
               applicationComplete="iniciar()">

    <fx:Style>
        .titulo { font-size: 22px; font-weight: bold; color: #1C4E80; }
    </fx:Style>

    <j:valuesImpl>
        <js:SimpleCSSValuesImpl/>          <!-- OBRIGATÓRIO -->
    </j:valuesImpl>

    <j:beads>
        <js:ApplicationDataBinding/>       <!-- OBRIGATÓRIO se houver {bindings} no documento -->
    </j:beads>

    <fx:Script><![CDATA[ ... ]]></fx:Script>

    <j:initialView>
        <j:View width="100%" height="100%">
            <j:beads><j:VerticalLayout gap="3"/></j:beads>
            <!-- conteúdo visual -->
        </j:View>
    </j:initialView>
</j:Application>
```

Regras:

- **Namespaces Flex proibidos:** `library://ns.adobe.com/flex/mx`, `library://ns.adobe.com/flex/spark`
  e `http://www.adobe.com/2006/mxml` não podem aparecer.
- Todo o visual fica dentro de `<j:initialView>`. O `<fx:Script>` pode ficar direto na Application, e
  os `localId` do initialView são acessíveis a partir do script.
- Use `applicationComplete` no lugar de `creationComplete` da Application Flex.
- Um componente MXML separado (ex.: `views/MinhaTela.mxml` com raiz `<j:View>`) precisa do bead
  `<js:ContainerDataBinding/>` em `<j:beads>` se usar bindings.

## 3. Identificadores, estilos e propriedades

| Flex | Royale Jewel |
|---|---|
| `id="txtNome"` | `localId="txtNome"` (use sempre `localId` dentro de MXML) |
| `styleName="titulo"` | `className="titulo"` |
| `label="Salvar"` em Button | `text="Salvar"` |
| `enabled="{cond}"` | **não existe** em Jewel. Use o bead `<j:beads><j:Disabled disabled="{!cond}"/></j:beads>` ou valide no handler (`if (ocupado) return;`) |
| `toolTip="..."` | remova, ou use o bead `<j:ToolTip toolTip="..."/>` |
| `maxChars="120"` | remova (a validação fica no backend e no handler) |
| `required="true"` em FormItem | escreva o asterisco no próprio label: `label="Nome *"` |
| `paddingTop`, `verticalGap`, `backgroundColor` | CSS em `<fx:Style>` + `className`, ou `gap` nos layouts |
| `rowCount="3"` em List | `height="90"` |
| `setFocus()` | remova |
| `FlexGlobals.topLevelApplication.parameters` | não existe; use um valor fixo (ex.: base da API `"api"`) |
| `new Date().time` | `new Date().getTime()` |

## 4. Mapeamento de componentes (MX → Jewel)

| Flex MX | Royale Jewel | Observações |
|---|---|---|
| `mx:Application` | `j:Application` + `j:initialView` + `j:View` | ver o esqueleto |
| `mx:VBox` | `j:VGroup` (ou `j:View` com `j:VerticalLayout`) | `gap="N"` (1 unidade ≈ 4px) |
| `mx:HBox` | `j:HGroup` | `itemsVerticalAlign="itemsCenter"` para centralizar |
| `mx:HDividedBox` / `mx:VDividedBox` | `j:HGroup` / `j:VGroup` | não há divisor arrastável |
| `mx:Panel title="X"` | `j:Card` > `j:CardHeader` (`<html:H4 text="X"/>`) + `j:CardPrimaryContent` | título dinâmico: `<html:H4 text="{variavel}"/>` |
| `mx:ControlBar` | `j:CardActions itemsHorizontalAlign="itemsRight"` | último filho do `j:Card` |
| `mx:Label` | `j:Label` | `text`, `className` |
| `mx:Text` | `j:Label multiline="true"` | |
| `mx:Button label=` | `j:Button text=` | `emphasis="primary"` para o botão principal |
| `mx:TextInput` | `j:TextInput` | o evento `enter` existe; placeholder: `<j:beads><j:TextPrompt prompt="..."/></j:beads>` |
| `mx:TextArea` | `j:TextArea` | |
| `mx:CheckBox` | `j:CheckBox` | `selected` |
| `mx:ComboBox` | `j:ComboBox` ou `j:DropDownList` | `dataProvider`, `selectedItem` |
| `mx:List` | `j:List` | `dataProvider` = `ArrayList`; `selectedIndex` e `selectedItem` |
| `mx:DataGrid` | `j:DataGrid` | ver a seção 5 |
| `mx:DataGridColumn headerText= dataField=` | `j:DataGridColumn label= dataField=` | `columnWidth="50"` no lugar de `width` |
| `mx:Form` / `mx:FormItem` / `mx:FormHeading` | `j:Form` / `j:FormItem` / `j:FormHeading` | `label` nos três |
| `mx:Spacer width="100%"` | `j:Spacer width="100%"` | |
| `mx:Alert` | `org.apache.royale.jewel.Alert` | ver a seção 7 |

## 5. DataGrid

```xml
<j:DataGrid localId="grade" width="100%" height="520"
            dataProvider="{contatos}" change="aoSelecionar()">
    <j:columns>
        <j:DataGridColumn label="ID" dataField="id" columnWidth="50"/>
        <j:DataGridColumn label="Nome" dataField="nome"/>
        <j:DataGridColumn label="Telefone" dataField="telefones" labelFunction="rotuloTelefone"/>
    </j:columns>
</j:DataGrid>
```

```actionscript
import org.apache.royale.jewel.supportClasses.datagrid.IDataGridColumnList;

// assinatura do labelFunction no Jewel: (item, IDataGridColumnList)
private function rotuloTelefone(item:Object, col:IDataGridColumnList):String { ... }
```

- A coluna com `labelFunction` precisa de um `dataField`, mesmo que o valor exibido venha da função.
- O evento `change` não precisa receber `event`. Leia `grade.selectedItem` e `grade.selectedIndex`.
- Para limpar a seleção, use `grade.selectedIndex = -1`. Não existe `scrollToIndex`.
- Prefira `height` fixo em pixels (ex.: `520`) dentro de `j:Card`: é o padrão testado.

## 5.1 Formulários (larguras)

- Dentro de `j:FormItem`, `width="100%"` em `j:TextInput` **não expande** o campo. Use largura fixa
  (ex.: `width="320"`).
- Um `j:List` vazio com `width="100%"` dentro de `j:HGroup` encolhe. Use largura fixa (ex.: `width="280"`)
  e `height` fixo.

## 5.2 Alturas de containers: não corte o formulário

- **Nunca** use `height` fixo em um `j:Card` (ou `j:CardPrimaryContent`) que contém um `j:Form`.
  O Jewel aplica `overflow: hidden` no conteúdo do Card, então os campos que passam da altura ficam
  **invisíveis e sem barra de rolagem**. O usuário não consegue preencher esses campos.
- Deixe o Card do formulário sem `height`: ele cresce com o conteúdo e a página rola.
- Altura fixa em pixels vale só para o componente de dados em si (ex.: `j:DataGrid height="520"`),
  nunca para o Card que envolve um formulário.
- Para dois painéis lado a lado (substituindo `mx:HDividedBox`), use `j:HGroup` com `width` em
  porcentagem nos Cards e **sem** `height` no HGroup e nos Cards.

```xml
<j:HGroup width="100%" gap="4">
    <j:Card width="55%">  ... <j:DataGrid height="520" .../> ... </j:Card>
    <j:Card width="45%">  ... <j:Form> ... </j:Form> ... </j:Card>   <!-- sem height -->
</j:HGroup>
```

## 6. Coleções

- `mx.collections.ArrayCollection` → `org.apache.royale.collections.ArrayList`.
- A API é a mesma para o uso comum: `new ArrayList(array)`, `length`, `getItemAt`, `addItem`,
  `removeItemAt`, `getItemIndex`, `source`.
- Um `[Bindable] public var lista:ArrayList` ligado a `dataProvider="{lista}"` atualiza a tela ao
  **reatribuir** a variável e também ao usar `addItem` e `removeItemAt`.
- Declare como `public` as variáveis `[Bindable]` usadas em bindings.

## 7. Alert e confirmação

```actionscript
import org.apache.royale.jewel.Alert;
import org.apache.royale.events.CloseEvent;
import org.apache.royale.jewel.beads.models.AlertModel;

Alert.show("Mensagem", "Título");                       // simples, botão OK

var alerta:Alert = new Alert();                         // confirmação com rótulos traduzidos
alerta.title = "Confirmação";
alerta.message = "Excluir o contato?";
alerta.flags = Alert.YES | Alert.NO;
var modelo:AlertModel = alerta.model as AlertModel;
if (modelo != null) { modelo.yesLabel = "Sim"; modelo.noLabel = "Não"; }
alerta.addEventListener(CloseEvent.CLOSE, aoFechar);    // e.detail == Alert.YES
alerta.showModal();
```

- As propriedades estáticas `Alert.yesLabel` e `Alert.noLabel` do Flex **não existem**. Use o AlertModel.
- `Alert.show(msg, titulo, flags, parent, handler)` do Flex **não recebe handler** no Jewel. Use
  `addEventListener(CloseEvent.CLOSE, ...)`.

## 8. HTTP / REST (`mx.rpc.http.HTTPService` → `org.apache.royale.net.HTTPService`)

```actionscript
import org.apache.royale.events.Event;
import org.apache.royale.net.HTTPConstants;
import org.apache.royale.net.HTTPService;

var servico:HTTPService = new HTTPService();
servico.url = url;
servico.method = HTTPConstants.POST;          // ou HTTPConstants.GET
servico.contentType = "application/json";
servico.contentData = JSON.stringify(corpo);  // só em POST
servico.addEventListener(HTTPConstants.COMPLETE, function(e:Event):void {
    if (servico.status != 200) { falha("HTTP " + servico.status); return; }
    var dados:Object = JSON.parse(servico.data);   // servico.data = texto da resposta
    ok(dados);
});
servico.addEventListener(HTTPConstants.IO_ERROR, function(e:Event):void { falha("Falha de rede"); });
servico.send();
```

- Não existem `ResultEvent`, `FaultEvent`, `resultFormat`, `useProxy` nem `requestTimeout`.
- `JSON.parse` e `JSON.stringify` funcionam normalmente.
- **Contrato da API:** mantenha exatamente as mesmas URLs, parâmetros e métodos do cliente Flex
  (ex.: `?suppress_response_codes=true`, `POST` + `&_method=PUT|DELETE`, `_ts` anti-cache).
  O backend Java 7 não pode mudar.
- Use a URL base relativa `"api"`. A aplicação HTML5 é servida pelo nginx, que encaminha `/api` ao backend.

## 9. ActionScript: o que muda

- Closures (`function(e:Event):void {...}`), `RegExp` literal, `Array`, `Object`, `String`, `Number`,
  `int`, `isNaN`, `encodeURIComponent` e `try/catch`: **iguais**.
- O acesso dinâmico `obj.campo` a objetos vindos de JSON funciona com
  `-js-dynamic-access-unknown-members=true`. Em objetos JSON, prefira `obj["campo"]` quando o nome
  vier de uma variável.
- `flash.events.*` → `org.apache.royale.events.*` (`Event`, `MouseEvent`, `KeyboardEvent`, `CloseEvent`).
- `mx.events.ListEvent` → não é necessário (use `change="handler()"` sem parâmetro).
- `mx.utils.StringUtil.trim` → `s.replace(/^\s+|\s+$/g, "")`.
- `import org.apache.royale.jewel.List;` para tipar parâmetros `List` (o nome `List` não conflita).

## 10. Erros comuns do compilador e correções

| Mensagem do compilador | Causa / correção |
|---|---|
| `This tag could not be resolved to an ActionScript class` | Tag inexistente no Jewel (ex.: `j:Panel`, `j:HBox`). Troque conforme a tabela da seção 4. |
| `This attribute is unexpected. It will be ignored.` | Propriedade Flex que não existe no Jewel (`enabled`, `styleName`, `maxChars`, `toolTip`, `label` em Button, `required`, `rowCount`). **É tratado como erro.** Veja a seção 3. |
| `Access of possibly undefined property X` | Nome errado, `localId` ausente ou propriedade Flex inexistente. |
| `Definition X could not be found` | Import de pacote Flex (`mx.*`, `flash.*`, `spark.*`). Troque pelo equivalente `org.apache.royale.*`. |
| `Call to a possibly undefined method X` | Método Flex inexistente (`setFocus`, `scrollToIndex`, `callLater`). Remova ou substitua. |
| `Implicit coercion of a value of type X to an unrelated type Y` | Tipagem. Use `as Tipo` ou declare `Object`. |
| `Incorrect number of arguments` | Assinatura diferente (ex.: `Alert.show` com handler). Veja a seção 7. |
| O `id` não é encontrado no script | Use `localId` no MXML. |
| (sem erro) campos do formulário somem da tela | `height` fixo no `j:Card` que contém o `j:Form`. Remova o `height` (veja a seção 5.2). |

## 11. Estrutura esperada do projeto Royale

```
royale/
└── src/
    ├── <Principal>.mxml          # mesmo nome do arquivo principal Flex
    └── <pacotes>/...as           # mesma estrutura de pacotes do Flex (ex.: br/ufpi/agenda/ApiClient.as)
```

Mantenha nomes de classes, pacotes e funções iguais aos do Flex sempre que possível, para facilitar a
rastreabilidade (o pipeline confere se as funções da origem ainda existem no destino).
